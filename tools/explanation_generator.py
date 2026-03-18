"""AI-powered pick explanation generator for the CFB agent.

Builds a structured feature snapshot from the database, then uses Groq
llama-3.3-70b-versatile to produce short and full natural-language
explanations for each model pick.
"""

import os
import json
from datetime import datetime, timezone

from db.database import query_db

FEATURE_DESCRIPTIONS = {
    "home_rushingYards": {
        "label": "Home Rushing Yards",
        "description": "Season rushing yards per game for the home team.",
    },
    "away_rushingYards": {
        "label": "Away Rushing Yards",
        "description": "Season rushing yards per game for the away team.",
    },
    "diff_rushingYards": {
        "label": "Rushing Yards Diff",
        "description": "Home minus away rushing yards per game differential.",
    },
    "home_turnovers": {
        "label": "Home Turnovers",
        "description": "Season turnover total for the home team.",
    },
    "away_turnovers": {
        "label": "Away Turnovers",
        "description": "Season turnover total for the away team.",
    },
    "diff_turnovers": {
        "label": "Turnovers Diff",
        "description": "Home minus away turnover differential (positive = home turns it over more).",
    },
    "home_fumblesLost": {
        "label": "Home Fumbles Lost",
        "description": "Season fumbles lost by the home team.",
    },
    "away_fumblesLost": {
        "label": "Away Fumbles Lost",
        "description": "Season fumbles lost by the away team.",
    },
    "diff_fumblesLost": {
        "label": "Fumbles Lost Diff",
        "description": "Home minus away fumbles-lost differential.",
    },
    "sp_overall_diff": {
        "label": "SP+ Overall Diff",
        "description": "Home minus away SP+ overall rating. Positive = home team is rated better overall.",
    },
    "sp_off_vs_def": {
        "label": "SP+ Off vs Def",
        "description": "Home offense SP+ rating minus away defense SP+ rating. Positive = home offense has an edge.",
    },
    "sp_def_vs_off": {
        "label": "SP+ Def vs Off",
        "description": "Away offense SP+ rating minus home defense SP+ rating. Lower = better for the home team.",
    },
    "sp_special_diff": {
        "label": "SP+ Special Teams Diff",
        "description": "Home minus away special teams SP+ rating differential.",
    },
    "rec_3yr_diff": {
        "label": "3-Year Recruiting Avg Diff",
        "description": "Difference in 3-year rolling average recruiting class points (home minus away).",
    },
    "ret_ppa_diff": {
        "label": "Returning Production PPA Diff",
        "description": "Home minus away returning production total PPA differential.",
    },
    "ret_pct_diff": {
        "label": "Returning Production % Diff",
        "description": "Home minus away returning production percentage differential.",
    },
    "home_new_coach": {
        "label": "Home New Coach",
        "description": "1 if the home team has a coach in their first year at this school, 0 otherwise.",
    },
    "away_new_coach": {
        "label": "Away New Coach",
        "description": "1 if the away team has a coach in their first year at this school, 0 otherwise.",
    },
    "coach_win_pct_diff": {
        "label": "Coach Career Win % Diff",
        "description": "Home coach career win percentage minus away coach career win percentage.",
    },
    "elo_diff": {
        "label": "Elo Rating Diff",
        "description": "Home minus away end-of-prior-season Elo rating differential.",
    },
    "talent_diff": {
        "label": "Talent Composite Diff",
        "description": "Home minus away team talent composite score differential.",
    },
    "neutral_site": {
        "label": "Neutral Site",
        "description": "1 if the game is played at a neutral site, 0 otherwise.",
    },
    "home_field": {
        "label": "Home Field Advantage",
        "description": "1 if the home team has a true home-field advantage (not neutral site), 0 otherwise.",
    },
}


def build_feature_snapshot(
    home_team: str, away_team: str, game_id: str, season: int
) -> dict:
    """Query all relevant tables and assemble a structured feature snapshot.

    Pulls SP+ ratings, Elo ratings, recruiting rankings, returning production,
    portal net ratings, talent composites, and coach records for both teams in
    the given season.  Returns a dict that can be passed directly to the
    explanation generation functions.

    Args:
        home_team: Home team name as it appears in the database.
        away_team: Away team name as it appears in the database.
        game_id: Pick's game_id (string) — stored in the snapshot for tracing.
        season: Season year.

    Returns:
        Dict with keys: home_team, away_team, game_id, season,
        snapshot_timestamp, and features (list of dicts with name/value/label/
        description).
    """
    import joblib

    _saved = os.path.join(os.path.dirname(__file__), "..", "models", "saved")
    feature_cols = joblib.load(os.path.join(_saved, "feature_cols.pkl"))

    # --- Load all reference tables ---
    sp_df = query_db(
        'SELECT year, team, rating, offense_rating, defense_rating, "specialTeams_rating" '
        "FROM sp_ratings"
    )
    elo_df = query_db("SELECT year, team, elo FROM elo_ratings")
    rec_df = query_db("SELECT year, team, points FROM recruiting_rankings")
    ret_df = query_db(
        'SELECT season AS year, team, "totalPPA" AS ret_totalPPA, "percentPPA" AS ret_percentPPA '
        "FROM returning_production"
    )
    portal_df = query_db(
        "SELECT season AS year, team, net_portal_score FROM portal_net_ratings"
    )
    talent_df = query_db("SELECT year, team, talent FROM talent")
    coaches_df = query_db(
        'SELECT school, year, "firstName", "lastName", wins, losses, games FROM coaches'
    )

    import numpy as np
    import pandas as pd

    # --- SP+ values ---
    def _sp_vals(team):
        row = sp_df[(sp_df["team"] == team) & (sp_df["year"] == season)]
        if row.empty:
            return 0.0, 0.0, 0.0, 0.0
        r = row.iloc[0]
        return (
            float(r["rating"] or 0),
            float(r["offense_rating"] or 0),
            float(r["defense_rating"] or 0),
            float(r["specialTeams_rating"] or 0),
        )

    h_sp, h_sp_off, h_sp_def, h_sp_st = _sp_vals(home_team)
    a_sp, a_sp_off, a_sp_def, a_sp_st = _sp_vals(away_team)

    # --- Elo ---
    def _elo(team):
        row = elo_df[(elo_df["team"] == team) & (elo_df["year"] == season)]
        return float(row.iloc[0]["elo"] or 0) if not row.empty else 0.0

    # --- Recruiting (3-year rolling avg) ---
    rec_sorted = rec_df.sort_values(["team", "year"])
    rec_sorted["rec_3yr_avg"] = (
        rec_sorted.groupby("team", sort=False)["points"]
        .transform(lambda s: s.rolling(3, min_periods=1).mean())
    )

    def _rec(team):
        row = rec_sorted[(rec_sorted["team"] == team) & (rec_sorted["year"] == season)]
        return float(row.iloc[0]["rec_3yr_avg"] or 0) if not row.empty else 0.0

    # --- Returning production ---
    def _ret(team):
        row = ret_df[(ret_df["team"] == team) & (ret_df["year"] == season)]
        if row.empty:
            return 0.0, 0.0
        r = row.iloc[0]
        return float(r["ret_totalppa"] or 0), float(r["ret_percentppa"] or 0)

    h_ret_ppa, h_ret_pct = _ret(home_team)
    a_ret_ppa, a_ret_pct = _ret(away_team)

    # --- Talent ---
    def _talent(team):
        row = talent_df[(talent_df["team"] == team) & (talent_df["year"] == season)]
        return float(row.iloc[0]["talent"] or 0) if not row.empty else 0.0

    # --- Coaches ---
    coaches_sorted = coaches_df.sort_values(["firstName", "lastName", "year"])
    min_yr = coaches_sorted.groupby(["school", "firstName", "lastName"])["year"].transform("min")
    coaches_sorted["is_new"] = (coaches_sorted["year"] == min_yr).astype(int)
    coaches_sorted["wins"] = pd.to_numeric(coaches_sorted["wins"], errors="coerce").fillna(0)
    coaches_sorted["games"] = pd.to_numeric(coaches_sorted["games"], errors="coerce").fillna(0)
    coaches_sorted["career_wins"] = coaches_sorted.groupby(["firstName", "lastName"])["wins"].cumsum()
    coaches_sorted["career_games"] = coaches_sorted.groupby(["firstName", "lastName"])["games"].cumsum()
    coaches_sorted["career_win_pct"] = (
        coaches_sorted["career_wins"] / coaches_sorted["career_games"].replace(0, np.nan)
    ).fillna(0.5)

    def _coach(team):
        row = coaches_sorted[(coaches_sorted["school"] == team) & (coaches_sorted["year"] == season)]
        if row.empty:
            return 0, 0.5
        r = row.iloc[0]
        return int(r["is_new"]), float(r["career_win_pct"] or 0.5)

    h_new, h_wpct = _coach(home_team)
    a_new, a_wpct = _coach(away_team)

    # --- Team stats (rushing yards, turnovers, fumbles lost) ---
    stats_df = query_db(
        'SELECT season, team, "statName", "statValue" FROM team_stats '
        f"WHERE season = {season} AND team IN ('{home_team}', '{away_team}')"
    )

    def _stat(team, stat_name):
        row = stats_df[(stats_df["team"] == team) & (stats_df["statName"] == stat_name)]
        return float(row.iloc[0]["statValue"] or 0) if not row.empty else 0.0

    h_rush = _stat(home_team, "rushingYards")
    a_rush = _stat(away_team, "rushingYards")
    h_to   = _stat(home_team, "turnovers")
    a_to   = _stat(away_team, "turnovers")
    h_fum  = _stat(home_team, "fumblesLost")
    a_fum  = _stat(away_team, "fumblesLost")

    # --- Assemble feature values in model order ---
    feature_values = {
        "home_rushingYards": h_rush,
        "away_rushingYards": a_rush,
        "diff_rushingYards": h_rush - a_rush,
        "home_turnovers": h_to,
        "away_turnovers": a_to,
        "diff_turnovers": h_to - a_to,
        "home_fumblesLost": h_fum,
        "away_fumblesLost": a_fum,
        "diff_fumblesLost": h_fum - a_fum,
        "sp_overall_diff": h_sp - a_sp,
        "sp_off_vs_def": h_sp_off - a_sp_def,
        "sp_def_vs_off": a_sp_off - h_sp_def,
        "sp_special_diff": h_sp_st - a_sp_st,
        "rec_3yr_diff": _rec(home_team) - _rec(away_team),
        "ret_ppa_diff": h_ret_ppa - a_ret_ppa,
        "ret_pct_diff": h_ret_pct - a_ret_pct,
        "home_new_coach": h_new,
        "away_new_coach": a_new,
        "coach_win_pct_diff": h_wpct - a_wpct,
        "elo_diff": _elo(home_team) - _elo(away_team),
        "talent_diff": _talent(home_team) - _talent(away_team),
        "neutral_site": 0,
        "home_field": 1,
    }

    features_list = []
    for col in feature_cols:
        desc = FEATURE_DESCRIPTIONS.get(col, {"label": col, "description": col})
        features_list.append({
            "name": col,
            "value": round(float(feature_values.get(col, 0.0)), 4),
            "label": desc["label"],
            "description": desc["description"],
        })

    return {
        "home_team": home_team,
        "away_team": away_team,
        "game_id": game_id,
        "season": season,
        "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
        "features": features_list,
    }


def generate_explanation_short(
    feature_snapshot: dict,
    win_prob: float,
    spread: float,
    pick_team: str,
) -> str:
    """Generate a concise 2–3 sentence AI analysis of a pick.

    Calls Groq llama-3.3-70b-versatile at temperature=0.1.  Returns a
    fallback string if the API call fails.

    Args:
        feature_snapshot: Structured dict from build_feature_snapshot().
        win_prob: Calibrated win probability for the pick team (0–1).
        spread: Consensus betting line spread (home perspective).
        pick_team: Name of the team being picked.

    Returns:
        2–3 sentence analysis string, or a fallback string on error.
    """
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        feature_summary = "\n".join(
            f"  {f['label']}: {f['value']}"
            for f in feature_snapshot["features"]
        )

        user_prompt = (
            f"Game: {feature_snapshot['away_team']} @ {feature_snapshot['home_team']}\n"
            f"Season: {feature_snapshot['season']}\n"
            f"Pick team: {pick_team}\n"
            f"Model win probability: {win_prob * 100:.1f}%\n"
            f"Consensus spread: {spread:+.1f}\n\n"
            f"Key model features:\n{feature_summary}\n\n"
            "Write exactly 2–3 sentences of sharp, numbers-first analysis explaining "
            "why this pick has edge. Lead with the strongest quantitative signal."
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a sharp, data-driven college football analyst. "
                        "Write concise, numbers-first analysis. No generic takes. "
                        "No jargon. Speak to a recreational bettor who understands "
                        "sports but not advanced analytics. "
                        "All statistics and feature values are based on historical season data "
                        "used to project future performance. Always frame statistics as historical "
                        "context, not current form. Say 'averaged X rushing yards last season' not "
                        "'has X rushing yards'. Say 'returned 74% of their production from last "
                        "season' not 'returns 74%'. Never present model features as real-time or "
                        "current game stats."
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:  # noqa: BLE001
        return (
            f"{pick_team} is the model's pick with a {win_prob * 100:.1f}% win probability. "
            f"Analysis unavailable at this time ({type(exc).__name__})."
        )


def generate_explanation_full(
    feature_snapshot: dict,
    win_prob: float,
    spread: float,
    pick_team: str,
) -> str:
    """Generate a detailed 5–7 sentence AI analysis of a pick.

    Covers the top 3 driving features by magnitude, line value context, and
    a sentence on risk/uncertainty.  Calls Groq llama-3.3-70b-versatile at
    temperature=0.1.  Returns a fallback string if the API call fails.

    Args:
        feature_snapshot: Structured dict from build_feature_snapshot().
        win_prob: Calibrated win probability for the pick team (0–1).
        spread: Consensus betting line spread (home perspective).
        pick_team: Name of the team being picked.

    Returns:
        5–7 sentence analysis string, or a fallback string on error.
    """
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        # Sort features by absolute value to surface the biggest signals
        sorted_features = sorted(
            feature_snapshot["features"],
            key=lambda f: abs(f["value"]),
            reverse=True,
        )
        top_features = sorted_features[:8]  # top 8 for context
        feature_summary = "\n".join(
            f"  {f['label']}: {f['value']}"
            for f in top_features
        )

        user_prompt = (
            f"Game: {feature_snapshot['away_team']} @ {feature_snapshot['home_team']}\n"
            f"Season: {feature_snapshot['season']}\n"
            f"Pick team: {pick_team}\n"
            f"Model win probability: {win_prob * 100:.1f}%\n"
            f"Consensus spread: {spread:+.1f}\n\n"
            f"Top model features by magnitude:\n{feature_summary}\n\n"
            "Write exactly 5���7 sentences of detailed analysis. Cover the top 3 "
            "driving features by magnitude with specific numbers, explain what the "
            "line value context means for the bettor, and close with one sentence on "
            "the main risk or source of uncertainty in this pick."
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a sharp, data-driven college football analyst. "
                        "Write concise, numbers-first analysis. No generic takes. "
                        "No jargon. Speak to a recreational bettor who understands "
                        "sports but not advanced analytics. "
                        "All statistics and feature values are based on historical season data "
                        "used to project future performance. Always frame statistics as historical "
                        "context, not current form. Say 'averaged X rushing yards last season' not "
                        "'has X rushing yards'. Say 'returned 74% of their production from last "
                        "season' not 'returns 74%'. Never present model features as real-time or "
                        "current game stats."
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:  # noqa: BLE001
        return (
            f"{pick_team} is the model's pick with a {win_prob * 100:.1f}% win probability. "
            f"Full analysis unavailable at this time ({type(exc).__name__})."
        )


def generate_and_store_explanation(pick_id: str) -> dict:
    """Generate AI explanations for a pick and upsert them into pick_explanations.

    Fetches the pick from the picks table, builds a feature snapshot, calls
    both explanation generators, then upserts the result into pick_explanations
    (INSERT ... ON CONFLICT (pick_id) DO UPDATE).

    Args:
        pick_id: UUID string identifying the row in the picks table.

    Returns:
        Dict representing the stored explanation row, with keys:
        pick_id, explanation_short, explanation_full, feature_snapshot,
        model_version, generated_at.

    Raises:
        ValueError: If the pick_id is not found in the picks table.
    """
    from sqlalchemy import text
    from db.database import engine
    from models.win_probability import MODEL_VERSION

    # Fetch the pick
    picks_df = query_db(
        f"SELECT * FROM picks WHERE id = '{pick_id}' LIMIT 1"
    )
    if picks_df.empty:
        raise ValueError(f"Pick not found: {pick_id}")

    pick = picks_df.iloc[0]
    home_team  = pick["home_team"]
    away_team  = pick["away_team"]
    game_id    = str(pick["game_id"])
    season     = int(pick["season"])
    win_prob   = float(pick["win_probability"])
    spread     = float(pick["spread"]) if pick["spread"] not in ("", None) else 0.0
    pick_team  = pick["pick_team"]

    snapshot = build_feature_snapshot(home_team, away_team, game_id, season)
    short_text = generate_explanation_short(snapshot, win_prob, spread, pick_team)
    full_text  = generate_explanation_full(snapshot, win_prob, spread, pick_team)

    generated_at = datetime.now(timezone.utc).isoformat()

    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO pick_explanations
                    (pick_id, explanation_short, explanation_full,
                     feature_snapshot, model_version, generated_at)
                VALUES
                    (:pick_id, :explanation_short, :explanation_full,
                     CAST(:feature_snapshot AS jsonb), :model_version, NOW())
                ON CONFLICT (pick_id) DO UPDATE SET
                    explanation_short = EXCLUDED.explanation_short,
                    explanation_full  = EXCLUDED.explanation_full,
                    feature_snapshot  = EXCLUDED.feature_snapshot,
                    model_version     = EXCLUDED.model_version,
                    generated_at      = EXCLUDED.generated_at
            """),
            {
                "pick_id": pick_id,
                "explanation_short": short_text,
                "explanation_full": full_text,
                "feature_snapshot": json.dumps(snapshot),
                "model_version": MODEL_VERSION,
            },
        )

    return {
        "pick_id": pick_id,
        "explanation_short": short_text,
        "explanation_full": full_text,
        "feature_snapshot": snapshot,
        "model_version": MODEL_VERSION,
        "generated_at": generated_at,
    }
