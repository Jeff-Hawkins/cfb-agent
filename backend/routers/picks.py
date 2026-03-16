"""Router for the /picks endpoints.

Handles pick flagging, approval/rejection, outcome tracking, and history.
All POST endpoints require a Bearer token matching the ADMIN_API_KEY env var.
"""

import os
import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text
from db.database import engine, query_db

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

    model_implied_spread is computed from the home team's win probability:
        model_implied = (home_win_prob - 0.5) * 28

    Args:
        win_prob: Home team win probability from the model.
        consensus_spread: Home team spread from betting_lines (negative = home favored).

    Returns:
        Absolute point difference between model and market.
    """
    model_implied = (win_prob - 0.5) * 28
    return abs(model_implied - consensus_spread)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/flag")
def flag_picks(
    season: int = Query(..., description="Season year"),
    week: int = Query(..., description="Week number"),
    _: None = Depends(_require_admin),
):
    """Flag picks for a given season and week.

    For each FBS game in the week, runs the LightGBM model and compares to
    consensus betting lines. Flags picks where win_probability >= 0.65 AND
    model_spread_diff >= 3.0. Inserts into picks table (skips duplicates).
    Sends email notification when at least one pick is flagged.

    Performance note: model and all data tables are loaded once before the
    game loop to avoid ~300+ redundant DB queries and file loads.
    """
    import os
    import joblib
    import pandas as pd
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

    # Pre-load model and all reference tables once — reused for every game
    if season == 2026:
        from models.win_probability import _predict_from_preseason_composite as _preseason_pred
        _model = None
        _feature_cols = None
        _profiles = _sp = _rec = _ret = _coa = _elo = _talent = _available_stats = None
    else:
        from models.win_probability import (
            build_team_profiles,
            _load_sp, _load_recruiting, _load_returning,
            _load_coaches, _load_elo, _load_talent,
            _build_features,
        )
        _saved = os.path.join(os.path.dirname(__file__), "..", "models", "saved")
        _model        = joblib.load(os.path.join(_saved, "win_prob_model.pkl"))
        _feature_cols = joblib.load(os.path.join(_saved, "feature_cols.pkl"))

        _profiles = build_team_profiles()
        _key_stats = ["pointsPerGame", "passingYards", "rushingYards", "turnovers", "fumblesLost"]
        _available_stats = [s for s in _key_stats if s in _profiles.columns]
        _profiles = _profiles[["team", "season"] + _available_stats].fillna(0)

        _sp     = _load_sp()
        _rec    = _load_recruiting()
        _ret    = _load_returning()
        _coa    = _load_coaches()
        _elo    = _load_elo()
        _talent = _load_talent()

    flagged = []

    for _, game in games_df.iterrows():
        game_id = str(game["id"])
        home    = game["homeTeam"]
        away    = game["awayTeam"]
        neutral = bool(game["neutralSite"])

        # Predict using pre-loaded data
        if season == 2026:
            home_win_prob = _preseason_pred(home, away, "preseason_2026")
        else:
            feats = _build_features(
                home, away, season,
                _profiles, _sp, _rec, _ret, _coa, _available_stats, _elo, _talent, neutral,
            )
            if feats is None:
                logger.warning("No features for %s vs %s %d", home, away, season)
                continue
            home_win_prob = float(_model.predict_proba(pd.DataFrame([feats])[_feature_cols])[0][1])

        if isinstance(home_win_prob, str):
            logger.warning("No prediction for %s vs %s: %s", home, away, home_win_prob)
            continue

        # Determine pick team — whichever side clears the 65% threshold
        if home_win_prob >= 0.65:
            pick_team = home
            pick_win_prob = float(home_win_prob)
        elif (1.0 - home_win_prob) >= 0.65:
            pick_team = away
            pick_win_prob = round(1.0 - float(home_win_prob), 4)
        else:
            continue  # Neither side meets threshold

        consensus_spread = lines_map.get(game_id)
        if consensus_spread is None:
            logger.warning("No betting line for game_id %s (%s vs %s)", game_id, home, away)
            continue

        diff = compute_model_spread_diff(float(home_win_prob), float(consensus_spread))
        if diff < 3.0:
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
            "spread": float(consensus_spread),
            "model_spread_diff": round(diff, 2),
            "confidence_label": label,
        }

        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO picks (
                        game_id, season, week, home_team, away_team, pick_team,
                        win_probability, spread, model_spread_diff, confidence_label
                    ) VALUES (
                        :game_id, :season, :week, :home_team, :away_team, :pick_team,
                        :win_probability, :spread, :model_spread_diff, :confidence_label
                    )
                    ON CONFLICT (game_id) DO NOTHING
                """),
                pick_row,
            )

        flagged.append(pick_row)

    if flagged:
        try:
            send_picks_ready_email(flagged, week, season)
        except Exception as exc:
            logger.error("Email notification failed: %s", exc)

    return {"flagged": len(flagged)}


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
    """Approve a pick by UUID, recording the approval timestamp."""
    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE picks SET approved = true, approval_timestamp = NOW() WHERE id = :id"),
            {"id": pick_id},
        )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Pick not found")
    return {"approved": True, "pick_id": pick_id}


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
