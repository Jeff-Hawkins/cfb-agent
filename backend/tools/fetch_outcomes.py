import requests
import pandas as pd
from dotenv import load_dotenv
import os
import logging
from sqlalchemy import text
from db.database import query_db, engine

load_dotenv()

API_KEY = os.getenv("CFB_API_KEY")
BASE_URL = "https://api.collegefootballdata.com"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

logger = logging.getLogger(__name__)

def fetch_game_outcomes(season: int, week: int) -> list[dict]:
    """Fetch completed game scores from CFBD and resolve ATS results.
    
    Args:
        season: Season year.
        week: Week number.
        
    Returns:
        List of resolved outcome dicts.
    """
    url = f"{BASE_URL}/games"
    params = {"year": season, "week": week, "seasonType": "regular"}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    
    if not isinstance(data, list) or len(data) == 0:
        logger.warning(f"No games found for {season} week {week}")
        return []

    # Get betting lines for spread resolution
    lines_df = query_db(f"SELECT game_id, spread FROM betting_lines WHERE season = {season} AND week = {week}")
    lines_map = dict(zip(lines_df["game_id"].astype(str), lines_df["spread"]))

    outcomes = []
    updated_count = 0
    
    for g in data:
        # Only process completed games
        if not g.get("completed") and (g.get("home_points") is None or g.get("away_points") is None):
            continue
            
        game_id = str(g["id"])
        home_score = g["home_points"]
        away_score = g["away_points"]
        home_team = g["home_team"]
        away_team = g["away_team"]
        
        if home_score is None or away_score is None:
            continue

        # Game Result
        if home_score > away_score:
            game_result = 'home_win'
        elif away_score > home_score:
            game_result = 'away_win'
        else:
            game_result = 'push'

        # ATS Result
        spread = lines_map.get(game_id)
        ats_result = None
        home_covered = None
        away_covered = None
        
        if spread is not None:
            spread = float(spread)
            margin = home_score - away_score
            # home covers if: margin > -spread
            if margin > -spread:
                ats_result = 'home_covered'
                home_covered = True
                away_covered = False
            elif margin < -spread:
                ats_result = 'away_covered'
                home_covered = False
                away_covered = True
            else:
                ats_result = 'push'
                home_covered = False
                away_covered = False

        outcome_row = {
            "game_id": game_id,
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score,
            "away_score": away_score,
            "game_result": game_result,
            "ats_result": ats_result,
            "home_covered": home_covered,
            "away_covered": away_covered
        }
        
        # Upsert into game_outcomes
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO game_outcomes (
                    game_id, home_team, away_team, home_score, away_score, 
                    game_result, ats_result, home_covered, away_covered, fetched_at
                ) VALUES (
                    :game_id, :home_team, :away_team, :home_score, :away_score, 
                    :game_result, :ats_result, :home_covered, :away_covered, NOW()
                )
                ON CONFLICT (game_id) DO UPDATE SET
                    home_score = EXCLUDED.home_score,
                    away_score = EXCLUDED.away_score,
                    game_result = EXCLUDED.game_result,
                    ats_result = EXCLUDED.ats_result,
                    home_covered = EXCLUDED.home_covered,
                    away_covered = EXCLUDED.away_covered,
                    fetched_at = NOW()
            """), outcome_row)
            updated_count += 1
            
        outcomes.append(outcome_row)

    # Log to cron_log
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO cron_log (job_name, records_updated, status)
            VALUES ('fetch_outcomes', :count, 'success')
        """), {"count": updated_count})

    return outcomes

def update_pick_outcomes(season: int, week: int) -> int:
    """Join picks table with game_outcomes and update picks.outcome.
    
    Args:
        season: Season year.
        week: Week number.
        
    Returns:
        Count of picks updated.
    """
    # Fetch approved picks with NULL outcome for the given season/week
    picks_to_update = query_db(f"""
        SELECT p.id, p.pick_team, p.home_team, p.away_team, 
               go.home_covered, go.away_covered, go.ats_result
        FROM picks p
        JOIN game_outcomes go ON go.game_id = p.game_id
        WHERE p.season = {season} AND p.week = {week}
          AND p.approved = true
          AND p.outcome IS NULL
    """)
    
    if picks_to_update.empty:
        return 0
        
    updated_count = 0
    for _, pick in picks_to_update.iterrows():
        outcome = None
        if pick['ats_result'] == 'push':
            outcome = 'PUSH'
        elif pick['pick_team'] == pick['home_team']:
            outcome = 'WIN' if pick['home_covered'] else 'LOSS'
        elif pick['pick_team'] == pick['away_team']:
            outcome = 'WIN' if pick['away_covered'] else 'LOSS'
            
        if outcome:
            with engine.begin() as conn:
                conn.execute(text("UPDATE picks SET outcome = :outcome WHERE id = :id"), 
                           {"outcome": outcome, "id": str(pick['id'])})
                updated_count += 1
                
    return updated_count

def run_sunday_pipeline(season: int, week: int) -> dict:
    """Run the Sunday pipeline: fetch outcomes and update picks.
    
    Args:
        season: Season year.
        week: Week number.
        
    Returns:
        Summary dict.
    """
    errors = []
    outcomes_fetched = 0
    picks_updated = 0
    
    try:
        outcomes = fetch_game_outcomes(season, week)
        outcomes_fetched = len(outcomes)
    except Exception as e:
        errors.append(f"fetch_game_outcomes failed: {str(e)}")
        
    try:
        picks_updated = update_pick_outcomes(season, week)
    except Exception as e:
        errors.append(f"update_pick_outcomes failed: {str(e)}")
        
    return {
        "outcomes_fetched": outcomes_fetched,
        "picks_updated": picks_updated,
        "errors": errors
    }
