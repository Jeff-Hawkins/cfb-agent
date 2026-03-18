import pandas as pd
from dotenv import load_dotenv
import os
import logging
from sqlalchemy import text
from db.database import query_db, engine

load_dotenv()

logger = logging.getLogger(__name__)

def snapshot_closing_lines(season: int, week: int) -> int:
    """Query betting_lines for games matching season + week and upsert into closing_lines.
    
    This uses the 'consensus' betting_lines as a proxy for the closing line.
    
    Args:
        season: Season year.
        week: Week number.
        
    Returns:
        Count of lines snapped.
    """
    lines_df = query_db(f"""
        SELECT game_id, season, week, home_team, away_team, spread, over_under
        FROM betting_lines 
        WHERE season = {season} AND week = {week}
    """)
    
    if lines_df.empty:
        logger.warning(f"No betting lines found to snapshot for {season} week {week}")
        return 0
        
    snapped_count = 0
    for _, line in lines_df.iterrows():
        closing_row = {
            "game_id": str(line["game_id"]),
            "season": int(line["season"]),
            "week": int(line["week"]),
            "home_team": line["home_team"],
            "away_team": line["away_team"],
            "closing_spread": float(line["spread"]) if line["spread"] is not None else None,
            "closing_total": float(line["over_under"]) if line["over_under"] is not None else None,
            "source": 'consensus'
        }
        
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO closing_lines (
                    game_id, season, week, home_team, away_team, 
                    closing_spread, closing_total, source, snapped_at
                ) VALUES (
                    :game_id, :season, :week, :home_team, :away_team, 
                    :closing_spread, :closing_total, :source, NOW()
                )
                ON CONFLICT (game_id) DO UPDATE SET
                    closing_spread = EXCLUDED.closing_spread,
                    closing_total = EXCLUDED.closing_total,
                    source = EXCLUDED.source,
                    snapped_at = NOW()
            """), closing_row)
            snapped_count += 1
            
    # Log to cron_log
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO cron_log (job_name, records_updated, status)
            VALUES ('snapshot_closing_lines', :count, 'success')
        """), {"count": snapped_count})
        
    return snapped_count
