"""Fetcher for per-team PPA ratings and success rates from CFBD.

This module provides functions to fetch, parse, and store team PPA ratings
using the CFBD /ppa/teams endpoint.
"""

import os
import requests
import logging
from sqlalchemy import text
from db.database import engine, query_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = os.getenv("CFB_API_KEY")
BASE_URL = "https://api.collegefootballdata.com"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def fetch_ppa_ratings(season: int) -> list[dict]:
    """Fetch per-team PPA and success rate from CFBD /ppa/teams.
    
    Args:
        season: The season year.
        
    Returns:
        List of dicts with parsed PPA ratings.
    """
    url = f"{BASE_URL}/ppa/teams"
    params = {"year": season}
    
    logger.info(f"Fetching PPA ratings for {season}...")
    response = requests.get(url, headers=HEADERS, params=params)
    
    if response.status_code != 200:
        logger.error(f"Failed to fetch PPA ratings: {response.status_code} - {response.text}")
        return []
        
    data = response.json()
    if not data:
        logger.warning(f"No PPA ratings found for {season}")
        return []
        
    parsed = []
    for item in data:
        team = item.get("team")
        off = item.get("offense", {})
        dfn = item.get("defense", {})
        
        # PPA ratings
        off_ppa = off.get("overall")
        def_ppa = dfn.get("overall")
        
        # Success rates (Note: these might be missing in /ppa/teams response)
        # Based on Task 3, we expect them here.
        sr_off = off.get("successRate")
        sr_def = dfn.get("successRate")
        
        if sr_off is None:
            logger.debug(f"successRate missing for {team} offense in /ppa/teams")
        if sr_def is None:
            logger.debug(f"successRate missing for {team} defense in /ppa/teams")
            
        parsed.append({
            "team": team,
            "season": season,
            "offense_ppa": off_ppa,
            "defense_ppa": def_ppa,
            "success_rate_offense": sr_off,
            "success_rate_defense": sr_def
        })
        
    return parsed

def upsert_ppa_ratings(season: int) -> None:
    """Fetch and upsert PPA ratings into the ppa_ratings table.
    
    Args:
        season: The season year.
    """
    ratings = fetch_ppa_ratings(season)
    if not ratings:
        return
        
    upsert_sql = """
    INSERT INTO ppa_ratings (
        team, season, offense_ppa, defense_ppa, success_rate_offense, success_rate_defense
    ) VALUES (
        :team, :season, :offense_ppa, :defense_ppa, :success_rate_offense, :success_rate_defense
    )
    ON CONFLICT (team, season) DO UPDATE SET
        offense_ppa = EXCLUDED.offense_ppa,
        defense_ppa = EXCLUDED.defense_ppa,
        success_rate_offense = EXCLUDED.success_rate_offense,
        success_rate_defense = EXCLUDED.success_rate_defense,
        created_at = NOW()
    """
    
    count = 0
    with engine.begin() as conn:
        for r in ratings:
            conn.execute(text(upsert_sql), r)
            count += 1
            
    logger.info(f"Upserted {count} PPA ratings for {season}")

def backfill_ppa_ratings(start: int = 2021, end: int = 2024) -> None:
    """Backfill PPA ratings for a range of seasons.
    
    Args:
        start: Start year (inclusive).
        end: End year (inclusive).
    """
    for season in range(start, end + 1):
        upsert_ppa_ratings(season)
    
    logger.info("Backfill complete.")

if __name__ == "__main__":
    import sys
    # For testing: fetch one season and print the first item
    if len(sys.argv) > 1:
        season = int(sys.argv[1])
        res = fetch_ppa_ratings(season)
        if res:
            print("First item from response:")
            print(res[0])
            upsert_ppa_ratings(season)
    else:
        # Default backfill
        backfill_ppa_ratings()
