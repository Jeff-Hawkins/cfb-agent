import pandas as pd
from dotenv import load_dotenv
import os
import logging
from sqlalchemy import text
from db.database import query_db, engine

load_dotenv()

logger = logging.getLogger(__name__)

def calculate_and_store_clv(season: int) -> int:
    """Calculate CLV for approved picks and store in clv_records.
    
    Args:
        season: Season year.
        
    Returns:
        Count of CLV records created.
    """
    # Query approved picks for the season that have an outcome and no CLV record yet
    picks_df = query_db(f"""
        SELECT p.id, p.game_id, p.pick_team, p.home_team, p.away_team, p.pick_spread, p.outcome,
               bl.spread as betting_line_spread,
               cl.closing_spread
        FROM picks p
        LEFT JOIN clv_records clv ON clv.pick_id = p.id
        LEFT JOIN betting_lines bl ON bl.game_id = p.game_id
        LEFT JOIN closing_lines cl ON cl.game_id = p.game_id
        WHERE p.season = {season}
          AND p.approved = true
          AND p.outcome IS NOT NULL
          AND clv.id IS NULL
    """)
    
    if picks_df.empty:
        return 0
        
    created_count = 0
    for _, pick in picks_df.iterrows():
        # 1. Get pick_spread (from pick perspective)
        p_spread = pick['pick_spread']
        if p_spread is None:
            # Derive for legacy picks
            bl_spread = pick['betting_line_spread']
            if bl_spread is None:
                continue
            if pick['pick_team'] == pick['home_team']:
                p_spread = float(bl_spread)
            else:
                p_spread = -1.0 * float(bl_spread)
        else:
            p_spread = float(p_spread)
            
        # 2. Get closing_spread (from pick perspective)
        c_spread_raw = pick['closing_spread']
        if c_spread_raw is None:
            continue
            
        c_spread_raw = float(c_spread_raw)
        if pick['pick_team'] == pick['home_team']:
            c_spread = c_spread_raw
        else:
            c_spread = -1.0 * c_spread_raw
            
        # 3. Calculate CLV
        # clv = pick_spread - closing_spread
        # If I got -7 and it closed -8, clv = -7 - (-8) = +1 (Beat the close by 1 pt)
        # If I got +3 and it closed +2, clv = 3 - 2 = +1 (Beat the close by 1 pt)
        clv = p_spread - c_spread
        clv_positive = clv > 0
        
        clv_row = {
            "pick_id": str(pick["id"]),
            "game_id": str(pick["game_id"]),
            "pick_team": pick["pick_team"],
            "pick_spread": p_spread,
            "closing_spread": c_spread,
            "clv": round(clv, 2),
            "clv_positive": clv_positive,
            "outcome": pick["outcome"]
        }
        
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO clv_records (
                    pick_id, game_id, pick_team, pick_spread, 
                    closing_spread, clv, clv_positive, outcome
                ) VALUES (
                    :pick_id, :game_id, :pick_team, :pick_spread, 
                    :closing_spread, :clv, :clv_positive, :outcome
                )
            """), clv_row)
            created_count += 1
            
    # Log to cron_log
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO cron_log (job_name, records_updated, status)
            VALUES ('calculate_clv', :count, 'success')
        """), {"count": created_count})
        
    return created_count

def get_clv_summary(season: int) -> dict:
    """Get summary CLV statistics for a given season.
    
    Args:
        season: Season year.
        
    Returns:
        Summary dict.
    """
    df = query_db(f"""
        SELECT clv, clv_positive, outcome
        FROM clv_records cr
        JOIN picks p ON p.id = cr.pick_id
        WHERE p.season = {season}
    """)
    
    if df.empty:
        return {
            "season": season,
            "total_picks": 0,
            "clv_positive_count": 0,
            "clv_positive_pct": 0.0,
            "avg_clv": 0.0,
            "avg_clv_wins": 0.0,
            "avg_clv_losses": 0.0
        }
        
    total_picks = len(df)
    clv_pos = df[df['clv_positive'] == True]
    clv_pos_count = len(clv_pos)
    
    avg_clv = df['clv'].mean()
    
    wins = df[df['outcome'] == 'WIN']
    losses = df[df['outcome'] == 'LOSS']
    
    avg_clv_wins = wins['clv'].mean() if not wins.empty else 0.0
    avg_clv_losses = losses['clv'].mean() if not losses.empty else 0.0
    
    return {
        "season": int(season),
        "total_picks": int(total_picks),
        "clv_positive_count": int(clv_pos_count),
        "clv_positive_pct": round((clv_pos_count / total_picks) * 100, 1),
        "avg_clv": round(float(avg_clv), 2),
        "avg_clv_wins": round(float(avg_clv_wins), 2),
        "avg_clv_losses": round(float(avg_clv_losses), 2)
    }
