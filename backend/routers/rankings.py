"""Router for the /rankings endpoint.

Returns all teams from the preseason_2026 composite ratings table, sorted
descending by composite score, with conference info joined from sp_ratings.
"""

from fastapi import APIRouter
from db.database import query_db

router = APIRouter()


@router.get("")
def get_rankings():
    """Return all teams ranked by 2026 preseason composite rating.

    Joins preseason_2026 with sp_ratings (2025) to include conference.
    Teams are ranked 1–N by composite_100 descending.
    """
    df = query_db("""
        SELECT
            p.team,
            s.conference,
            p.composite_100 AS composite_rating
        FROM preseason_2026 p
        LEFT JOIN sp_ratings s
            ON p.team = s.team AND s.year = 2025
        ORDER BY p.composite_100 DESC
    """)

    df.insert(0, "rank", range(1, len(df) + 1))
    df["composite_rating"] = df["composite_rating"].round(2)

    return df.to_dict(orient="records")
