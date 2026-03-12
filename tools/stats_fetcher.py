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
        print(f"No team stats data for {year}")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    save_to_db(df, "team_stats")
    return df

def fetch_betting_lines(year: int):
    url = f"{BASE_URL}/lines"
    params = {"year": year}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    if not isinstance(data, list) or len(data) == 0:
        print(f"No betting lines data for {year}")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    save_to_db(df, "betting_lines")
    return df

def fetch_sp_ratings(year: int):
    url = f"{BASE_URL}/ratings/sp"
    params = {"year": year}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    if not isinstance(data, list) or len(data) == 0:
        print(f"No SP+ ratings data for {year}")
        return pd.DataFrame()
    df = pd.json_normalize(data, sep="_")
    save_to_db(df, "sp_ratings")
    return df

def fetch_recruiting_rankings(year: int):
    url = f"{BASE_URL}/recruiting/teams"
    params = {"year": year}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    if not isinstance(data, list) or len(data) == 0:
        print(f"No recruiting rankings data for {year}")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    save_to_db(df, "recruiting_rankings")
    return df

def fetch_returning_production(year: int):
    url = f"{BASE_URL}/player/returning"
    params = {"year": year}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    if not isinstance(data, list) or len(data) == 0:
        print(f"No returning production data for {year}")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    save_to_db(df, "returning_production")
    return df

def fetch_coaches(year: int):
    url = f"{BASE_URL}/coaches"
    params = {"year": year}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    if not isinstance(data, list) or len(data) == 0:
        print(f"No coaches data for {year}")
        return pd.DataFrame()
    # Explode nested seasons array into one row per coach/team/year
    rows = []
    for coach in data:
        for season in coach.get("seasons", []):
            rows.append({
                "firstName": coach.get("firstName"),
                "lastName":  coach.get("lastName"),
                "hireDate":  coach.get("hireDate"),
                "school":    season.get("school"),
                "year":      season.get("year"),
                "games":     season.get("games"),
                "wins":      season.get("wins"),
                "losses":    season.get("losses"),
                "ties":      season.get("ties"),
                "preseasonRank": season.get("preseasonRank"),
                "postseasonRank": season.get("postseasonRank"),
            })
    if not rows:
        print(f"No coaches season records for {year}")
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    save_to_db(df, "coaches")
    return df