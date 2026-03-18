"""Router for the /picks endpoints.

Handles pick flagging, approval/rejection, outcome tracking, and history.
All POST endpoints require a Bearer token matching the ADMIN_API_KEY env var.
Public endpoints (GET /picks/public, GET /picks/pending, GET /picks/approved)
require no authentication.
"""

import os
import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text
from db.database import engine, query_db
from constants import MAX_ABS_SPREAD, MIN_SPREAD_DIFF, MIN_WIN_PROB_FLAG, MODEL_IMPLIED_SCALE

logger = logging.getLogger(__name__)

router = APIRouter()
_security = HTTPBearer()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _require_admin(credentials: HTTPAuthorizationCredentials = Depends(_security)):
    """Validate Bearer token against ADMIN_API_KEY env var."""
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected or credentials.credentials != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ---------------------------------------------------------------------------
# Background task helpers
# ---------------------------------------------------------------------------

def _run_explanation_bg(pick_id: str) -> None:
    """Generate and store an AI explanation for a pick in the background.

    Called as a FastAPI BackgroundTask immediately after a pick is inserted
    by flag_picks(). Wraps generate_and_store_explanation() in try/except
    so failures never surface to the flag response.

    Args:
        pick_id: UUID string of the newly inserted pick.
    """
    try:
        from tools.explanation_generator import generate_and_store_explanation
        generate_and_store_explanation(pick_id)
    except Exception as exc:
        logger.error("Background explanation generation failed for pick %s: %s", pick_id, exc)


# ---------------------------------------------------------------------------
# Pure helpers (importable for tests)
# ---------------------------------------------------------------------------

def confidence_label(win_prob: float) -> str:
    """Return confidence label for a given win probability.

    Args:
        win_prob: Pick team's win probability (0–1).

    Returns:
        'Lean' for 65–74%, 'Moderate' for 75–84%, 'Strong' for 85%+.
    """
    if win_prob >= 0.85:
        return "Strong"
    elif win_prob >= 0.75:
        return "Moderate"
    else:
        return "Lean"


def compute_model_spread_diff(win_prob: float, consensus_spread: float) -> float:
    """Return absolute difference between model-implied spread and consensus.

    Legacy helper kept for backward compatibility with existing tests.
    The flag endpoint now uses _directed_spread_diff() for correct sign handling.

    model_implied_spread is computed from the home team's win probability:
        model_implied = (home_win_prob - 0.5) * 28

    Args:
        win_prob: Home team win probability from the model.
        consensus_spread: Home team spread from betting_lines (negative = home favored).

    Returns:
        Absolute point difference between model and market.
    """
    model_implied = (win_prob - 0.5) * MODEL_IMPLIED_SCALE
    return abs(model_implied - consensus_spread)


def _directed_spread_diff(
    pick_win_prob: float,
    pick_team: str,
    home_team: str,
    actual_spread: float,
) -> float:
    """Compute signed spread_diff using the corrected directional formula.

    The model-implied spread is sign-adjusted based on which side was picked:
      - Home pick: model_implied = -1 * (win_prob - 0.5) * 28
      - Away pick: model_implied =  1 * (win_prob - 0.5) * 28

    spread_diff = actual_spread - model_implied

    Args:
        pick_win_prob: Win probability of the pick team (0–1).
        pick_team: Name of the team picked.
        home_team: Name of the home team.
        actual_spread: Consensus spread from betting_lines (home perspective,
            negative = home favored).

    Returns:
        Signed spread difference (actual minus model-implied).
    """
    if pick_team == home_team:
        model_implied = -1.0 * (pick_win_prob - 0.5) * MODEL_IMPLIED_SCALE
    else:
        model_implied = (pick_win_prob - 0.5) * MODEL_IMPLIED_SCALE
    return actual_spread - model_implied


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/flag")
def flag_picks(
    season: int = Query(..., description="Season year"),
    week: int = Query(..., description="Week number"),
    background_tasks: BackgroundTasks = None,
    _: None = Depends(_require_admin),
):
    """Flag picks for a given season and week.

    For each FBS game in the week, runs the LightGBM model (with Platt
    calibration) and compares to consensus betting lines.

    Flag thresholds (Phase 6):
      - abs(spread) <= 17 — removes blowouts
      - win_prob >= 0.65  — model confidence floor
      - abs(spread_diff) >= 5.0 — corrected model vs market disagreement

    spread_diff uses the directional formula:
      home pick: model_implied = -1 * (win_prob - 0.5) * 28
      away pick: model_implied =  1 * (win_prob - 0.5) * 28
      spread_diff = actual_spread - model_implied

    Inserts into the picks table (skips duplicates). Sends email notification
    when at least one pick is flagged.
    """
    from models.win_probability import predict_win_probability
    from services.notifications import send_picks_ready_email

    games_df = query_db(f"""
        SELECT id, "homeTeam", "awayTeam", "neutralSite"
        FROM games
        WHERE season = {season} AND week = {week}
          AND "seasonType" = 'regular'
          AND "homeClassification" = 'fbs'
          AND "awayClassification" = 'fbs'
    """)

    if games_df.empty:
        return {"flagged": 0}

    lines_df = query_db(f"""
        SELECT game_id, spread
        FROM betting_lines
        WHERE season = {season} AND week = {week}
    """)
    lines_map = dict(zip(lines_df["game_id"].astype(str), lines_df["spread"]))

    flagged = []

    for _, game in games_df.iterrows():
        game_id = str(game["id"])
        home    = game["homeTeam"]
        away    = game["awayTeam"]

        result = predict_win_probability(home, away, season)

        if isinstance(result, str):
            logger.warning("No prediction for %s vs %s: %s", home, away, result)
            continue

        if isinstance(result, dict):
            home_win_prob = result["win_prob"]
        else:
            home_win_prob = float(result)

        if isinstance(home_win_prob, str):
            logger.warning("No prediction for %s vs %s: %s", home, away, home_win_prob)
            continue

        # Determine pick team — whichever side clears the MIN_WIN_PROB_FLAG threshold
        if home_win_prob >= MIN_WIN_PROB_FLAG:
            pick_team = home
            pick_win_prob = float(home_win_prob)
        elif (1.0 - home_win_prob) >= MIN_WIN_PROB_FLAG:
            pick_team = away
            pick_win_prob = round(1.0 - float(home_win_prob), 4)
        else:
            continue  # Neither side meets win-prob threshold

        consensus_spread = lines_map.get(game_id)
        if consensus_spread is None:
            logger.warning("No betting line for game_id %s (%s vs %s)", game_id, home, away)
            continue

        spread_val = float(consensus_spread)

        # Blowout filter — skip games with large spreads
        if abs(spread_val) > MAX_ABS_SPREAD:
            continue

        # Corrected directional spread_diff
        spread_diff = _directed_spread_diff(pick_win_prob, pick_team, home, spread_val)
        if abs(spread_diff) < MIN_SPREAD_DIFF:
            continue

        label = confidence_label(pick_win_prob)

        pick_row = {
            "game_id": game_id,
            "season": season,
            "week": week,
            "home_team": home,
            "away_team": away,
            "pick_team": pick_team,
            "win_probability": round(pick_win_prob, 4),
            "spread": spread_val,
            "model_spread_diff": round(abs(spread_diff), 2),
            "confidence_label": label,
        }

        with engine.begin() as conn:
            inserted = conn.execute(
                text("""
                    INSERT INTO picks (
                        game_id, season, week, home_team, away_team, pick_team,
                        win_probability, spread, model_spread_diff, confidence_label
                    ) VALUES (
                        :game_id, :season, :week, :home_team, :away_team, :pick_team,
                        :win_probability, :spread, :model_spread_diff, :confidence_label
                    )
                    ON CONFLICT (game_id) DO NOTHING
                    RETURNING id
                """),
                pick_row,
            ).fetchone()

        if inserted:
            pick_id = str(inserted[0])
            flagged.append(pick_row)
            if background_tasks is not None:
                background_tasks.add_task(_run_explanation_bg, pick_id)

    if flagged:
        try:
            send_picks_ready_email(flagged, week, season)
        except Exception as exc:
            logger.error("Email notification failed: %s", exc)

    return {"flagged": len(flagged)}


@router.post("/recalculate-spreads")
def recalculate_spreads(
    _: None = Depends(_require_admin),
):
    """Recalculate model_spread_diff for all existing picks using the corrected formula.

    Uses the spread already stored on each pick row (originally sourced from
    betting_lines at flag time). Applies _directed_spread_diff() to get a
    corrected abs(spread_diff) and updates model_spread_diff on each row.

    Returns:
        Dict with count of picks updated.
    """
    picks_df = query_db("""
        SELECT id, pick_team, home_team, win_probability, spread
        FROM picks
        WHERE spread IS NOT NULL
    """)

    if picks_df.empty:
        return {"updated": 0}

    updated = 0
    for _, pick in picks_df.iterrows():
        try:
            spread_val = float(pick["spread"])
            win_prob   = float(pick["win_probability"])
            diff = _directed_spread_diff(win_prob, pick["pick_team"], pick["home_team"], spread_val)
            new_msd = round(abs(diff), 2)

            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE picks SET model_spread_diff = :msd WHERE id = :id"),
                    {"msd": new_msd, "id": str(pick["id"])},
                )
            updated += 1
        except Exception as exc:
            logger.warning("Could not recalculate spread diff for pick %s: %s", pick["id"], exc)

    return {"updated": updated}


@router.get("/public")
def get_public_picks(
    season: int = Query(..., description="Season year"),
    week: int = Query(None, description="Week number — omit for most recent week with picks"),
):
    """Return all approved picks for a season/week with AI explanation shorts.

    No authentication required — fully public endpoint.

    If week is omitted, returns the most recent week that has approved picks.
    Results are sorted by abs(model_spread_diff) descending.

    Args:
        season: Season year.
        week: CFB week number. Optional.

    Returns:
        List of pick dicts including explanation_short from pick_explanations
        (null if not yet generated).
    """
    if week is None:
        week_df = query_db(f"""
            SELECT week FROM picks
            WHERE season = {season} AND approved = true
            ORDER BY week DESC
            LIMIT 1
        """)
        if week_df.empty:
            return []
        week = int(week_df.iloc[0]["week"])

    df = query_db(f"""
        SELECT
            p.id, p.game_id, p.season, p.week,
            p.home_team, p.away_team, p.pick_team,
            p.win_probability, p.spread, p.model_spread_diff, p.confidence_label,
            p.outcome, p.ats_result, p.clv,
            pe.explanation_short
        FROM picks p
        LEFT JOIN pick_explanations pe ON pe.pick_id::text = p.id::text
        WHERE p.season = {season}
          AND p.week = {week}
          AND p.approved = true
          AND ABS(p.spread) <= 17
        ORDER BY ABS(p.model_spread_diff) DESC
    """)
    df = df.fillna("")
    return df.to_dict(orient="records")


@router.get("/pending")
def get_pending_picks():
    """Return picks not yet approved or rejected, ordered by win_probability desc."""
    df = query_db("""
        SELECT * FROM picks
        WHERE approved = false AND rejected = false
        ORDER BY win_probability DESC
    """)
    df = df.fillna("")
    return df.to_dict(orient="records")


@router.post("/{pick_id}/approve")
def approve_pick(
    pick_id: str,
    _: None = Depends(_require_admin),
):
    """Approve a pick by UUID, recording the approval timestamp and pick_spread.

    Explanations are generated at flag time via _run_explanation_bg(), so
    no additional generation is triggered here.
    """
    # 1. Fetch pick details to calculate pick_spread
    pick = query_db(f"SELECT game_id, pick_team, home_team FROM picks WHERE id = '{pick_id}'")
    if pick.empty:
        raise HTTPException(status_code=404, detail="Pick not found")
    
    p = pick.iloc[0]
    game_id = p['game_id']
    pick_team = p['pick_team']
    home_team = p['home_team']
    
    # 2. Look up current consensus spread
    line = query_db(f"SELECT spread FROM betting_lines WHERE game_id = '{game_id}'")
    pick_spread = None
    if not line.empty:
        spread = float(line.iloc[0]['spread'])
        # If pick_team == home_team: pick_spread = spread
        # If pick_team == away_team: pick_spread = -1 * spread
        if pick_team == home_team:
            pick_spread = spread
        else:
            pick_spread = -1.0 * spread

    # 3. Update pick with approved=True and pick_spread
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                UPDATE picks 
                SET approved = true, 
                    approval_timestamp = NOW(),
                    pick_spread = :pick_spread
                WHERE id = :id
            """),
            {"id": pick_id, "pick_spread": pick_spread},
        )
    
    return {"approved": True, "pick_id": pick_id, "pick_spread": pick_spread}


@router.post("/{pick_id}/reject")
def reject_pick(
    pick_id: str,
    _: None = Depends(_require_admin),
):
    """Reject a pick by UUID."""
    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE picks SET rejected = true WHERE id = :id"),
            {"id": pick_id},
        )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Pick not found")
    return {"rejected": True, "pick_id": pick_id}


@router.get("/approved")
def get_approved_picks():
    """Return all approved picks ordered by created_at desc."""
    df = query_db("""
        SELECT * FROM picks
        WHERE approved = true
        ORDER BY created_at DESC
    """)
    df = df.fillna("")
    return df.to_dict(orient="records")


@router.post("/update-outcomes")
def update_outcomes(
    season: int = Query(..., description="Season year"),
    week: int = Query(..., description="Week number"),
    _: None = Depends(_require_admin),
):
    """Update outcome and ATS result for approved picks in a given season/week.

    Queries final scores from the games table. Skips games without scores yet
    and returns retry=true so the caller knows to run again later.

    ATS result convention (spread is from home team's perspective, negative = home favored):
      - WIN  if pick team covered the spread
      - LOSS if pick team did not cover
      - PUSH if margin exactly equals the spread
    """
    picks_df = query_db(f"""
        SELECT id, game_id, pick_team, home_team, away_team, spread
        FROM picks
        WHERE season = {season} AND week = {week}
          AND approved = true
          AND outcome IS NULL
    """)

    if picks_df.empty:
        return {"updated": 0, "pending": 0, "retry": False}

    updated = 0
    pending = 0

    for _, pick in picks_df.iterrows():
        try:
            game_id_int = int(pick["game_id"])
        except (ValueError, TypeError):
            logger.warning("Non-integer game_id %s, skipping", pick["game_id"])
            pending += 1
            continue

        game_df = query_db(f"""
            SELECT "homeTeam", "awayTeam", "homePoints", "awayPoints"
            FROM games
            WHERE id = {game_id_int}
              AND "homePoints" IS NOT NULL
              AND "awayPoints" IS NOT NULL
        """)

        if game_df.empty:
            logger.warning("Scores not yet available for game_id %s", pick["game_id"])
            pending += 1
            continue

        g = game_df.iloc[0]
        home_pts = float(g["homePoints"])
        away_pts = float(g["awayPoints"])
        home_margin = home_pts - away_pts
        pick_team = pick["pick_team"]

        # Straight-up outcome
        if pick_team == g["homeTeam"]:
            outcome = "WIN" if home_pts > away_pts else "LOSS"
            sign = 1   # home perspective
        else:
            outcome = "WIN" if away_pts > home_pts else "LOSS"
            sign = -1  # away perspective (flip margin)

        # ATS: covered_margin = sign * (home_margin + spread)
        # spread is negative when home is favored (e.g. -7 means home gives 7)
        raw_spread = pick["spread"]
        if raw_spread == "" or raw_spread is None:
            ats_result = None
        else:
            spread_val = float(raw_spread)
            covered_margin = sign * (home_margin + spread_val)
            if abs(covered_margin) < 0.01:
                ats_result = "PUSH"
            elif covered_margin > 0:
                ats_result = "WIN"
            else:
                ats_result = "LOSS"

        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE picks
                    SET outcome = :outcome, ats_result = :ats_result
                    WHERE id = :pick_id
                """),
                {"outcome": outcome, "ats_result": ats_result, "pick_id": str(pick["id"])},
            )

        updated += 1

    return {"updated": updated, "pending": pending, "retry": pending > 0}
