from fastapi import APIRouter, Query
from db.database import query_db
from tools.calculate_clv import get_clv_summary

router = APIRouter()

@router.get("/summary")
def clv_summary(
    season: int = Query(..., description="Season year")
):
    """Return summary CLV statistics for a given season."""
    return get_clv_summary(season)

@router.get("/picks")
def clv_picks(
    season: int = Query(..., description="Season year")
):
    """Return all clv_records for the season joined with pick context.
    
    Ordered by week asc, then clv desc.
    """
    df = query_db(f"""
        SELECT 
            cr.game_id, cr.pick_team, cr.pick_spread, cr.closing_spread, 
            cr.clv, cr.clv_positive, cr.outcome,
            p.home_team, p.away_team, p.week
        FROM clv_records cr
        JOIN picks p ON p.id = cr.pick_id
        WHERE p.season = {season}
        ORDER BY p.week ASC, cr.clv DESC
    """)
    
    df = df.fillna("")
    return df.to_dict(orient="records")
