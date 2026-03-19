"""Scraper for Massey Ratings and comparison with SP+ power ratings.

This module scrapes Massey Ratings from the web, computes Z-scores,
and compares them with SP+ ratings in the power_ratings_comparison table.
"""

import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import logging
from sqlalchemy import text
from db.database import engine, query_db
from tools.utils.team_transformer import normalize_team_name, get_unmapped_teams

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_massey_ratings(season: int) -> list[dict]:
    """Scrape Massey ratings for a given season.
    
    Args:
        season: The season year.
        
    Returns:
        List of dicts: {team, season, massey_rating}
    """
    # URL strategy
    # Current season: https://www.masseyratings.com/cf/fbs/ratings
    # Historical: https://www.masseyratings.com/cf/fbs/{season}/ratings
    # Note: Massey site is dynamic and might block simple requests.
    # We use a browser-like User-Agent.
    
    is_current = (season == 2024 or season == 2025) # Adjust based on reality
    if is_current:
        url = "https://www.masseyratings.com/cf/fbs/ratings"
    else:
        # Massey sometimes uses different IDs for historical seasons
        # This is a best-effort guess
        url = f"https://www.masseyratings.com/cf/fbs/{season}/ratings"
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    logger.info(f"Scraping Massey ratings from {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            logger.warning(f"Massey URL returned {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error fetching Massey ratings: {e}")
        return []
        
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Strategy: Find the table with the most rows
    tables = soup.find_all("table")
    if not tables:
        logger.warning("No tables found on Massey ratings page. Site might be dynamic or blocking.")
        return []
        
    main_table = max(tables, key=lambda t: len(t.find_all("tr")))
    rows = main_table.find_all("tr")
    
    ratings = []
    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            continue
            
        # Skip header: check if rank is numeric
        rank_text = cells[0].get_text(strip=True)
        if not rank_text.isdigit():
            continue
            
        raw_team = cells[1].get_text(strip=True)
        # Some rows might have record or other info in team name, clean it
        # Massey often has "Team (Conf)" or just "Team"
        team_name = raw_team.split('(')[0].strip()
        
        rating_text = cells[2].get_text(strip=True)
        try:
            # Massey rating might have special characters or be formatted
            # Look for the first float-like string
            rating = float(rating_text.replace('+', ''))
        except ValueError:
            continue
            
        normalized_team = normalize_team_name(team_name)
        
        ratings.append({
            "team": normalized_team,
            "season": season,
            "massey_rating": rating,
            "raw_name": team_name
        })
        
    logger.info(f"Found {len(ratings)} Massey ratings for {season}")
    return ratings

def upsert_massey_ratings(season: int) -> None:
    """Fetch, compute Z-scores, and upsert Massey ratings.
    
    Args:
        season: The season year.
    """
    ratings_data = fetch_massey_ratings(season)
    if not ratings_data:
        # Fallback for testing if site is blocked: mock some data if we are in a dev environment
        # but for production we just skip.
        return
        
    df_massey = pd.DataFrame(ratings_data)
    
    # Compute Z-Massey
    mean_m = df_massey["massey_rating"].mean()
    std_m = df_massey["massey_rating"].std()
    df_massey["z_massey"] = (df_massey["massey_rating"] - mean_m) / std_m
    
    # Pull SP+ ratings for same season
    # Note: sp_ratings table uses 'year' and 'rating'
    sp_df = query_db(f"SELECT team, rating as sp_overall FROM sp_ratings WHERE year = {season}")
    
    if sp_df.empty:
        logger.warning(f"No SP+ ratings found for {season} to compare.")
        # We can still upsert Massey without Z-SP
        df_merged = df_massey
        df_merged["sp_overall"] = None
        df_merged["z_sp"] = None
        df_merged["composite_z"] = None
    else:
        # Compute Z-SP
        mean_sp = sp_df["sp_overall"].mean()
        std_sp = sp_df["sp_overall"].std()
        sp_df["z_sp"] = (sp_df["sp_overall"] - mean_sp) / std_sp
        
        # Merge
        df_merged = pd.merge(df_massey, sp_df, on="team", how="left")
        
        # Compute Composite Z
        # If z_sp is missing for a team, use z_massey
        df_merged["composite_z"] = df_merged.apply(
            lambda row: (row["z_massey"] + row["z_sp"]) / 2 if pd.notnull(row["z_sp"]) else row["z_massey"],
            axis=1
        )
        
    # Upsert
    upsert_sql = """
    INSERT INTO power_ratings_comparison (
        team, season, massey_rating, sp_overall, z_massey, z_sp, composite_z
    ) VALUES (
        :team, :season, :massey_rating, :sp_overall, :z_massey, :z_sp, :composite_z
    )
    ON CONFLICT (team, season) DO UPDATE SET
        massey_rating = EXCLUDED.massey_rating,
        sp_overall = EXCLUDED.sp_overall,
        z_massey = EXCLUDED.z_massey,
        z_sp = EXCLUDED.z_sp,
        composite_z = EXCLUDED.composite_z,
        created_at = NOW()
    """
    
    count = 0
    with engine.begin() as conn:
        for _, row in df_merged.iterrows():
            params = {
                "team": row["team"],
                "season": int(row["season"]),
                "massey_rating": float(row["massey_rating"]),
                "sp_overall": float(row["sp_overall"]) if pd.notnull(row["sp_overall"]) else None,
                "z_massey": float(row["z_massey"]),
                "z_sp": float(row["z_sp"]) if pd.notnull(row["z_sp"]) else None,
                "composite_z": float(row["composite_z"]) if pd.notnull(row["composite_z"]) else None
            }
            conn.execute(text(upsert_sql), params)
            count += 1
            
    logger.info(f"Upserted {count} power ratings comparison rows for {season}")

def backfill_massey_ratings(start: int = 2021, end: int = 2024) -> None:
    """Backfill Massey ratings and log unmatched teams.
    
    Args:
        start: Start year.
        end: End year.
    """
    all_unmatched = set()
    
    for season in range(start, end + 1):
        # Fetch raw ratings first to check names
        raw_ratings = fetch_massey_ratings(season)
        if not raw_ratings:
            continue
            
        raw_names = [r["raw_name"] for r in raw_ratings]
        unmapped = get_unmapped_teams(raw_names)
        
        # Pull known CFBD teams from games table to check if unmapped names match canonicals
        # (This is a more robust way to check unmatched teams)
        known_teams_df = query_db(f"SELECT DISTINCT \"homeTeam\" as team FROM games WHERE season = {season}")
        known_teams = set(known_teams_df["team"].tolist())
        
        real_unmatched = [name for name in unmapped if normalize_team_name(name) not in known_teams]
        
        matched_count = len(raw_names) - len(real_unmatched)
        logger.info(f"Season {season}: {matched_count} matched, {len(real_unmatched)} unmatched")
        
        if real_unmatched:
            print(f"Unmatched teams for {season}: {sorted(real_unmatched)}")
            all_unmatched.update(real_unmatched)
            
        # Perform actual upsert
        upsert_massey_ratings(season)
        
    if all_unmatched:
        print("\nTOTAL UNMATCHED TEAMS ACROSS ALL SEASONS:")
        print(sorted(list(all_unmatched)))

if __name__ == "__main__":
    backfill_massey_ratings()
