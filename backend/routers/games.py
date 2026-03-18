"""Router for the /games endpoints.

GET /games          — 2025 regular season FBS schedule, optionally by week.
GET /games/weekly   — FBS game predictions with model vs Vegas comparison.
"""

import logging
from fastapi import APIRouter, Query
from db.database import query_db
from constants import MAX_ABS_SPREAD, MIN_WIN_PROB_GAMES, MODEL_IMPLIED_SCALE

logger = logging.getLogger(__name__)

router = APIRouter()

P4_CONFERENCES = {'SEC', 'Big Ten', 'Big 12', 'ACC'}

def get_conference_group(home_conf: str, away_conf: str,
                         home_class: str, away_class: str) -> str | None:
    """
    Returns 'P4', 'G5', or None.
    None means skip this game (not FBS).
    If either team is P4 → 'P4'
    If both are FBS but neither is P4 → 'G5'
    If neither team is FBS → None (filter out)
    """
    is_fbs = home_class == 'fbs' or away_class == 'fbs'
    if not is_fbs:
        return None
    if home_conf in P4_CONFERENCES or away_conf in P4_CONFERENCES:
        return 'P4'
    return 'G5'


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
      home_score, away_score, status ('scheduled' | 'final'),
      conference_group ('P4' | 'G5').

    Sorted by model_edge descending — highest disagreement first.
    No authentication required.
    """
    from models.win_probability import predict_win_probability_batch

    # 1. Fetch FBS-only games (both home and away must be FBS)
    games_df = query_db(f"""
        SELECT id, "homeTeam", "awayTeam", "homePoints", "awayPoints",
               "neutralSite", "completed", "homeConference", "awayConference",
               "homeClassification", "awayClassification"
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

    # 4. Build game list for batch prediction
    game_list = [
        {
            "game_id":      str(row["id"]),
            "home_team":    row["homeTeam"],
            "away_team":    row["awayTeam"],
            "home_points":  row["homePoints"],
            "away_points":  row["awayPoints"],
            "neutral_site": bool(row["neutralSite"]) if row["neutralSite"] != "" else False,
            "home_conf":    row["homeConference"],
            "away_conf":    row["awayConference"],
            "home_class":   row["homeClassification"],
            "away_class":   row["awayClassification"],
        }
        for _, row in games_df.iterrows()
    ]

    # 5. Single batch prediction — loads model + all feature tables once
    predictions = predict_win_probability_batch(game_list, season)

    results = []

    for pred in predictions:
        game_id       = pred["game_id"]
        home_win_prob = pred["home_win_prob"]
        away_win_prob = pred["away_win_prob"]

        # Filter: skip near-coin-flip games (neither team >= MIN_WIN_PROB_GAMES)
        if max(home_win_prob, away_win_prob) < MIN_WIN_PROB_GAMES:
            continue

        # Model-implied spreads (mirrors: home + away = 0)
        home_implied_spread = round(-1.0 * (home_win_prob - 0.5) * MODEL_IMPLIED_SCALE, 1)
        away_implied_spread = round(-1.0 * (away_win_prob - 0.5) * MODEL_IMPLIED_SCALE, 1)

        # Consensus spread and model edge
        consensus_raw    = lines_map.get(game_id)
        consensus_spread = float(consensus_raw) if consensus_raw is not None else None

        # Blowout filter — exclude games where the line is extreme
        if consensus_spread is not None and abs(consensus_spread) > MAX_ABS_SPREAD:
            continue

        model_edge = (
            round(abs(consensus_spread - home_implied_spread), 1)
            if consensus_spread is not None else None
        )

        # Scores and status
        home_pts = pred["home_points"]
        away_pts = pred["away_points"]
        home_score = int(float(home_pts)) if home_pts != "" else None
        away_score = int(float(away_pts)) if away_pts != "" else None
        status = "final" if (home_score is not None and away_score is not None) else "scheduled"

        # Conference group (P4/G5)
        conf_group = get_conference_group(
            pred["home_conf"], pred["away_conf"],
            pred["home_class"], pred["away_class"]
        )

        results.append({
            "game_id":             game_id,
            "season":              season,
            "week":                week,
            "home_team":           pred["home_team"],
            "away_team":           pred["away_team"],
            "home_win_prob":       home_win_prob,
            "away_win_prob":       away_win_prob,
            "home_implied_spread": home_implied_spread,
            "away_implied_spread": away_implied_spread,
            "consensus_spread":    consensus_spread,
            "model_edge":          model_edge,
            "has_approved_pick":   game_id in picks_map,
            "pick_team":           picks_map.get(game_id),
            "home_score":          home_score,
            "away_score":          away_score,
            "status":              status,
            "conference_group":    conf_group,
        })

    # Sort by model_edge descending; games without a line sort last
    results.sort(
        key=lambda x: x["model_edge"] if x["model_edge"] is not None else -1,
        reverse=True,
    )

    return results
