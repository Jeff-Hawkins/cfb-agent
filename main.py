from tools.stats_fetcher import fetch_games, fetch_team_stats, fetch_betting_lines
from db.database import query_db
from models.win_probability import predict_win_probability
import os

if __name__ == "__main__":
    # Fresh start each run
    if os.path.exists("data/cfb.db"):
        os.remove("data/cfb.db")
        print("Cleared existing database.")

    for year in [2021, 2022, 2023, 2024, 2025]:
        print(f"\nFetching {year} data...")
        fetch_games(year)
        fetch_team_stats(year)
        fetch_betting_lines(year)

    print("\nTotal games in DB:")
    print(query_db("SELECT season, COUNT(*) as game_count FROM games GROUP BY season"))

    print("\nOhio State vs Michigan win probability:")
    prob = predict_win_probability("Ohio State", "Michigan", 2024)
    print(f"Ohio State win probability: {prob}")