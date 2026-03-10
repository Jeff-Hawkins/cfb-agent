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
    data = response.json()
    if not isinstance(data, list) or len(data) == 0:
        print(f"No games data for {year}")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, (list, dict))).any():
            df[col] = df[col].apply(lambda x: str(x) if isinstance(x, (list, dict)) else x)
    save_to_db(df, "games")
    return df

def fetch_team_stats(year: int):
    url = f"{BASE_URL}/stats/season"
    params = {"year": year}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    if not isinstance(data, list) or len(data) == 0:
        print(f"No data for {year}")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df = pd.DataFrame(response.json())
    save_to_db(df, "team_stats")
    return df

def fetch_betting_lines(year: int):
    url = f"{BASE_URL}/lines"
    params = {"year": year}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    if not isinstance(data, list) or len(data) == 0:
        print(f"No data for {year}")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df = pd.DataFrame(response.json())
    save_to_db(df, "betting_lines")
    return df