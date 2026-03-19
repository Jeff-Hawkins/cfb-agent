import os
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from tools.fetch_outcomes import run_sunday_pipeline
from tools.calculate_clv import calculate_and_store_clv
from tools.snapshot_closing_lines import snapshot_closing_lines

logger = logging.getLogger(__name__)

router = APIRouter()
_security = HTTPBearer()

def _require_admin(credentials: HTTPAuthorizationCredentials = Depends(_security)):
    """Validate Bearer token against ADMIN_API_KEY env var."""
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected or credentials.credentials != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.post("/outcomes/refresh")
def refresh_outcomes(
    season: int = Query(..., description="Season year"),
    week: int = Query(..., description="Week number"),
    _: HTTPAuthorizationCredentials = Depends(_require_admin)
):
    """Trigger Sunday pipeline to fetch outcomes and update picks."""
    result = run_sunday_pipeline(season, week)
    return result

@router.post("/clv/calculate")
def calculate_clv(
    season: int = Query(..., description="Season year"),
    _: HTTPAuthorizationCredentials = Depends(_require_admin)
):
    """Trigger CLV calculation for approved picks in a season."""
    count = calculate_and_store_clv(season)
    return {"clv_records_created": count}

@router.post("/lines/snapshot")
def snapshot_lines(
    season: int = Query(..., description="Season year"),
    week: int = Query(..., description="Week number"),
    _: HTTPAuthorizationCredentials = Depends(_require_admin)
):
    """Trigger closing line snapshot for a season/week."""
    count = snapshot_closing_lines(season, week)
    return {"lines_snapped": count}

@router.post("/stats/refresh")
def refresh_stats(
    season: int = Query(..., description="Season year"),
    _: HTTPAuthorizationCredentials = Depends(_require_admin)
):
    """Trigger fetch of advanced stats for a season."""
    from tools.stats_fetcher import fetch_advanced_stats
    from tools.advanced_stats_updater import backfill_advanced_stats_extended
    
    # 1. Base advanced stats
    df = fetch_advanced_stats(season)
    # 2. Extended stats (success rate, havoc)
    backfill_advanced_stats_extended(start=season, end=season)
    
    return {"records_updated": len(df)}

@router.post("/ratings/refresh")
def refresh_ratings(
    season: int = Query(..., description="Season year"),
    _: HTTPAuthorizationCredentials = Depends(_require_admin)
):
    """Trigger fetch of PPA and Massey ratings for a season."""
    from tools.ppa_fetcher import upsert_ppa_ratings
    from tools.massey_scraper import upsert_massey_ratings
    
    upsert_ppa_ratings(season)
    upsert_massey_ratings(season)
    
    return {"status": "success"}
