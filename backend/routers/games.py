"""Router for the /games endpoint.

Returns 2025 regular season games for FBS home teams, optionally filtered
by week. Used to power the schedule-based matchup view in the frontend.
"""

from fastapi import APIRouter, Query
from db.database import query_db

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
