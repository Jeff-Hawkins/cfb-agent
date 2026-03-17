"""Router for the /games endpoints.

GET /games          — 2025 regular season FBS schedule, optionally by week.
GET /games/weekly   — FBS game predictions with model vs Vegas comparison.
"""

import logging
from fastapi import APIRouter, Query
from db.database import query_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("")
def get_games(week: int = Query(None, description="Filter by week number")):
    """Return 2025 regular season FBS games, optionally filtered by week.

    Includes home/away team names, points, neutral site flag, and
    away team classification so the UI can label FCS opponents.
    """
    week_filter = f'AND week = {week}' if week else ''

    df = query_db(f"""
        SELECT
            id,
            week,
            "homeTeam",
            "awayTeam",
            "homePoints",
            "awayPoints",
            "neutralSite",
            "homeConference",
            "awayConference",
            "awayClassification",
            "completed"
        FROM games
        WHERE season = 2025
        AND "seasonType" = 'regular'
        AND "homeClassification" = 'fbs'
        {week_filter}
        ORDER BY week, "homeTeam"
    """)

    df = df.fillna("")
    return df.to_dict(orient="records")


@router.get("/weekly")
def get_weekly_games(
    season: int = Query(..., description="Season year"),
    week: int = Query(..., description="Week number"),
):
    """Return FBS game predictions for a season/week with model vs Vegas comparison.

    For each FBS-vs-FBS game, runs the win probability model and computes
    model-implied spreads. Joins to betting_lines for the consensus spread
    and to picks for any approved pick on that game.

    Filters:
      - Both teams must be FBS (no FCS matchups).
      - max(home_win_prob, away_win_prob) >= 0.55 — at least one team has
        a meaningful model lean; near-coin-flip games are excluded.

    Returns per game:
      game_id, season, week, home_team, away_team,
      home_win_prob, away_win_prob,
      home_implied_spread, away_implied_spread,
      consensus_spread (home perspective, negative = home favored),
      model_edge (abs disagreement between consensus and home_implied),
      has_approved_pick (bool), pick_team (str or null),
      home_score, away_score, status ('scheduled' | 'final').

    Sorted by model_edge descending — highest disagreement first.
    No authentication required.
    """
    from models.win_probability import predict_win_probability

    # 1. Fetch FBS-only games (both home and away must be FBS)
    games_df = query_db(f"""
        SELECT id, "homeTeam", "awayTeam", "homePoints", "awayPoints", "completed"
        FROM games
        WHERE season = {season} AND week = {week}
          AND "seasonType" = 'regular'
          AND "homeClassification" = 'fbs'
          AND "awayClassification" = 'fbs'
        ORDER BY "homeTeam"
    """)

    if games_df.empty:
        return []

    games_df = games_df.fillna("")

    # 2. Fetch consensus betting lines
    lines_df = query_db(f"""
        SELECT game_id, spread
        FROM betting_lines
        WHERE season = {season} AND week = {week}
    """)
    lines_map = dict(zip(lines_df["game_id"].astype(str), lines_df["spread"]))

    # 3. Fetch approved picks for this week (one per game due to unique constraint)
    picks_df = query_db(f"""
        SELECT game_id, pick_team
        FROM picks
        WHERE season = {season} AND week = {week}
          AND approved = true
    """)
    picks_map = dict(zip(picks_df["game_id"].astype(str), picks_df["pick_team"]))

    results = []

    for _, game in games_df.iterrows():
        game_id = str(game["id"])
        home    = game["homeTeam"]
        away    = game["awayTeam"]

        # Run win probability model
        result = predict_win_probability(home, away, season)

        if isinstance(result, str):
            logger.warning("No prediction for %s vs %s: %s", home, away, result)
            continue

        if isinstance(result, dict):
            home_win_prob = float(result["win_prob"])
        else:
            home_win_prob = float(result)

        if isinstance(home_win_prob, str):
            logger.warning("No prediction for %s vs %s: %s", home, away, home_win_prob)
            continue

        away_win_prob = round(1.0 - home_win_prob, 4)

        # Filter: skip near-coin-flip games (neither team >= 55%)
        if max(home_win_prob, away_win_prob) < 0.55:
            continue

        # Model-implied spreads (pick team's perspective)
        home_implied_spread = round(-1.0 * (home_win_prob - 0.5) * 28, 1)
        away_implied_spread = round((away_win_prob - 0.5) * 28, 1)

        # Consensus spread and model edge
        consensus_raw = lines_map.get(game_id)
        consensus_spread = float(consensus_raw) if consensus_raw is not None else None
        model_edge = (
            round(abs(consensus_spread - home_implied_spread), 1)
            if consensus_spread is not None else None
        )

        # Scores and status
        home_score = int(float(game["homePoints"])) if game["homePoints"] != "" else None
        away_score = int(float(game["awayPoints"])) if game["awayPoints"] != "" else None
        status = "final" if (home_score is not None and away_score is not None) else "scheduled"

        results.append({
            "game_id":             game_id,
            "season":              season,
            "week":                week,
            "home_team":           home,
            "away_team":           away,
            "home_win_prob":       round(home_win_prob, 4),
            "away_win_prob":       round(away_win_prob, 4),
            "home_implied_spread": home_implied_spread,
            "away_implied_spread": away_implied_spread,
            "consensus_spread":    consensus_spread,
            "model_edge":          model_edge,
            "has_approved_pick":   game_id in picks_map,
            "pick_team":           picks_map.get(game_id),
            "home_score":          home_score,
            "away_score":          away_score,
            "status":              status,
        })

    # Sort by model_edge descending; games without a line sort last
    results.sort(
        key=lambda x: x["model_edge"] if x["model_edge"] is not None else -1,
        reverse=True,
    )

    return results
