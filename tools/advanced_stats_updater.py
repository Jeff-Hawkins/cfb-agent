"""Extends advanced_stats table with success rate and havoc metrics from CFBD.

This module provides functions to fetch and update existing advanced_stats rows
with offense success_rate and defense_havoc_total.
"""

import os
import requests
import logging
from sqlalchemy import text
from db.database import engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = os.getenv("CFB_API_KEY")
BASE_URL = "https://api.collegefootballdata.com"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def fetch_advanced_stats_extended(season: int) -> list[dict]:
    """Fetch advanced stats from CFBD and extract success rate and havoc.
    
    Args:
        season: The season year.
        
    Returns:
        List of dicts with team, season, success_rate, and defense_havoc_total.
    """
    url = f"{BASE_URL}/stats/season/advanced"
    params = {"year": season}
    
    logger.info(f"Fetching extended advanced stats for {season}...")
    response = requests.get(url, headers=HEADERS, params=params)
    
    if response.status_code != 200:
        logger.error(f"Failed to fetch advanced stats: {response.status_code} - {response.text}")
        return []
        
    data = response.json()
    if not data:
        logger.warning(f"No advanced stats found for {season}")
        return []
        
    parsed = []
    for item in data:
        team = item.get("team")
        off = item.get("offense", {})
        dfn = item.get("defense", {})
        
        # Pull specified metrics
        # offense.successRate
        success_rate = off.get("successRate")
        # defense.havoc.total
        def_havoc = dfn.get("havoc", {}).get("total")
        
        parsed.append({
            "team": team,
            "season": season,
            "success_rate": success_rate,
            "defense_havoc_total": def_havoc
        })
        
    return parsed

def backfill_advanced_stats_extended(start: int = 2021, end: int = 2024) -> None:
    """Update existing advanced_stats rows with success rate and havoc metrics.
    
    Args:
        start: Start year (inclusive).
        end: End year (inclusive).
    """
    for season in range(start, end + 1):
        stats = fetch_advanced_stats_extended(season)
        if not stats:
            continue
            
        update_sql = """
        UPDATE advanced_stats
        SET success_rate = :success_rate,
            defense_havoc_total = :defense_havoc_total
        WHERE team = :team AND season = :season
        """
        
        count = 0
        with engine.begin() as conn:
            for s in stats:
                # Only update if we have data to update
                if s["success_rate"] is not None or s["defense_havoc_total"] is not None:
                    conn.execute(text(update_sql), s)
                    count += 1
                    
        logger.info(f"Updated {count} advanced_stats rows for {season}")

if __name__ == "__main__":
    # Default backfill
    backfill_advanced_stats_extended()
