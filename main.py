from tools.stats_fetcher import (
    fetch_games, fetch_team_stats, fetch_betting_lines,
    fetch_sp_ratings, fetch_recruiting_rankings,
    fetch_returning_production, fetch_coaches,
    fetch_portal_players, build_portal_net_ratings,
)
from db.database import query_db, engine
from db.schema import create_all_tables
from sqlalchemy import text
from models.win_probability import predict_win_probability

FETCH_TABLES = [
    "games", "team_stats", "betting_lines", "sp_ratings",
    "recruiting_rankings", "returning_production", "coaches",
    "portal_players", "portal_net_ratings",
]

if __name__ == "__main__":
    # Ensure all tables exist before truncating
    create_all_tables()

    # Truncate all fetch tables for a clean rebuild
    with engine.connect() as conn:
        for table in FETCH_TABLES:
            conn.execute(text(f"TRUNCATE TABLE {table}"))
        conn.commit()
    print("Cleared existing data from all fetch tables.")

    for year in [2021, 2022, 2023, 2024, 2025]:
        print(f"\nFetching {year} data...")
        fetch_games(year)
        fetch_team_stats(year)
        fetch_betting_lines(year)
        fetch_sp_ratings(year)
        fetch_recruiting_rankings(year)
        fetch_returning_production(year)
        fetch_coaches(year)
        fetch_portal_players(year)
        build_portal_net_ratings(year)

    print("\nTotal games in DB:")
    print(query_db("SELECT season, COUNT(*) as game_count FROM games GROUP BY season"))

    print("\nOhio State vs Michigan win probability:")
    prob = predict_win_probability("Ohio State", "Michigan", 2024)
    print(f"Ohio State win probability: {prob}")