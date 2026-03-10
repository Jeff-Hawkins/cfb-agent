import requests
import pandas as pd
from dotenv import load_dotenv
import os
from db.database import save_to_db

load_dotenv()

API_KEY = os.getenv("CFB_API_KEY")
BASE_URL = "https://api.collegefootballdata.com"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def fetch_games(year: int, season_type: str = "regular"):
    url = f"{BASE_URL}/games"
    params = {"year": year, "seasonType": season_type}
    response = requests.get(url, headers=HEADERS, params=params)
    df = pd.DataFrame(response.json())
    save_to_db(df, "games")
    return df

def fetch_team_stats(year: int):
    url = f"{BASE_URL}/stats/season"
    params = {"year": year}
    response = requests.get(url, headers=HEADERS, params=params)
    df = pd.DataFrame(response.json())
    save_to_db(df, "team_stats")
    return df

def fetch_betting_lines(year: int):
    url = f"{BASE_URL}/lines"
    params = {"year": year}
    response = requests.get(url, headers=HEADERS, params=params)
    df = pd.DataFrame(response.json())
    save_to_db(df, "betting_lines")
    return df