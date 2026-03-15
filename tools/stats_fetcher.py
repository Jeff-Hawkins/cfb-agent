import requests
import pandas as pd
from dotenv import load_dotenv
import os
from db.database import save_to_db, query_db

load_dotenv()

API_KEY = os.getenv("CFB_API_KEY")
BASE_URL = "https://api.collegefootballdata.com"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def fetch_games(year: int, season_type: str = "regular"):
    """Fetch all games for a given season and save to the games table."""
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
    """Fetch season team stats for a given year and save to the team_stats table."""
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
    """Fetch betting lines for a given year and save to the betting_lines table.

    Explodes the nested lines list into one row per provider per game, then
    averages across providers to produce one consensus row per game.
    """
    url = f"{BASE_URL}/lines"
    params = {"year": year}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    if not isinstance(data, list) or len(data) == 0:
        print(f"No betting lines data for {year}")
        return pd.DataFrame()

    rows = []
    for game in data:
        base = {
            "game_id": game.get("id"),
            "season": game.get("season"),
            "week": game.get("week"),
            "home_team": game.get("homeTeam"),
            "away_team": game.get("awayTeam"),
            "home_score": game.get("homeScore"),
            "away_score": game.get("awayScore"),
        }
        for line in game.get("lines", []):
            row = base.copy()
            row["spread"] = line.get("spread")
            row["spread_open"] = line.get("spreadOpen")
            row["over_under"] = line.get("overUnder")
            row["over_under_open"] = line.get("overUnderOpen")
            row["home_moneyline"] = line.get("homeMoneyline")
            row["away_moneyline"] = line.get("awayMoneyline")
            rows.append(row)

    numeric_cols = ["spread", "spread_open", "over_under", "over_under_open",
                    "home_moneyline", "away_moneyline"]
    id_cols = ["game_id", "season", "week", "home_team", "away_team",
               "home_score", "away_score"]

    df = pd.DataFrame(rows)
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    df = (
        df.groupby(id_cols, as_index=False)[numeric_cols]
        .mean()
    )
    save_to_db(df, "betting_lines")
    return df

def fetch_sp_ratings(year: int):
    """Fetch SP+ ratings for a given year and save to the sp_ratings table."""
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
    """Fetch team recruiting rankings for a given year and save to the recruiting_rankings table."""
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
    """Fetch returning production PPA data for a given year and save to the returning_production table."""
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
    """Fetch head coach records for a given year, explode nested seasons, and save to the coaches table."""
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

def fetch_advanced_stats(year: int):
    """Fetch advanced team stats for a given year, flatten nested offense/defense objects,
    keep key columns, and save to the advanced_stats table."""
    url = f"{BASE_URL}/stats/season/advanced"
    params = {"year": year}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    if not isinstance(data, list) or len(data) == 0:
        print(f"No advanced stats data for {year}")
        return pd.DataFrame()
    df = pd.json_normalize(data, sep="_")
    keep = ["team", "season", "offense_havocAllowed", "offense_lineYards",
            "defense_stuffRate", "defense_passIsrRate", "defense_havocTotal"]
    cols = [c for c in keep if c in df.columns]
    df = df[cols]
    save_to_db(df, "advanced_stats")
    return df


def fetch_drives(year: int):
    """Fetch drive-level data for a given year and save to the drives table."""
    url = f"{BASE_URL}/drives"
    params = {"year": year, "seasonType": "regular"}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    if not isinstance(data, list) or len(data) == 0:
        print(f"No drives data for {year}")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    save_to_db(df, "drives")
    return df


def fetch_pregame_wp(year: int):
    """Fetch pregame win probability for every game in a given year and save to the pregame_wp table."""
    url = f"{BASE_URL}/metrics/wp/pregame"
    params = {"year": year}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    if not isinstance(data, list) or len(data) == 0:
        print(f"No pregame WP data for {year}")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    save_to_db(df, "pregame_wp")
    return df


def fetch_talent(year: int):
    """Fetch team talent composite scores for a given year and save to the talent table."""
    url = f"{BASE_URL}/talent"
    params = {"year": year}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    if not isinstance(data, list) or len(data) == 0:
        print(f"No talent data for {year}")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    save_to_db(df, "talent")
    return df


def fetch_elo_ratings(year: int):
    """Fetch end-of-season Elo ratings for a given year and save to the elo_ratings table."""
    url = f"{BASE_URL}/ratings/elo"
    params = {"year": year}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    if not isinstance(data, list) or len(data) == 0:
        print(f"No Elo ratings data for {year}")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    save_to_db(df, "elo_ratings")
    return df



ELIGIBILITY_WEIGHT = {"Immediate": 1.0, "Redshirt": 0.5}

def fetch_portal_players(year: int):
    """Fetch transfer portal players for a given year, apply eligibility weighting, and save to portal_players table."""
    url = f"{BASE_URL}/player/portal"
    params = {"year": year}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    if not isinstance(data, list) or len(data) == 0:
        print(f"No portal players data for {year}")
        return pd.DataFrame()

    df = pd.DataFrame(data)

    # Only keep completed transfers (destination known)
    df = df[df["destination"].notna()].copy()

    # Fill null stars with the position average, then fall back to 2.5
    pos_avg = df.groupby("position")["stars"].transform("mean")
    df["stars"] = df["stars"].fillna(pos_avg).fillna(2.5)

    # Eligibility weighting: Immediate=1.0, Redshirt=0.5, other=0.75
    df["elig_weight"]    = df["eligibility"].map(ELIGIBILITY_WEIGHT).fillna(0.75)
    df["weighted_stars"] = df["stars"] * df["elig_weight"]

    save_to_db(df, "portal_players")
    return df


def build_portal_net_ratings(year: int):
    """
    Aggregate portal_players into a per-team net rating for one season:
      net_portal_score = sum(weighted_stars incoming) - sum(weighted_stars outgoing)

    Only destination transfers to FBS programs are counted as incoming.
    Outgoing is still counted for all FBS origin teams regardless of where
    the player ended up, since the talent loss is real either way.
    FBS team universe is derived from the games table (homeClassification/awayClassification = 'fbs').
    """
    df = query_db(f"SELECT origin, destination, weighted_stars FROM portal_players WHERE season = {year}")
    if df.empty:
        print(f"No portal_players rows for {year} to aggregate")
        return pd.DataFrame()

    # Build FBS team set from games table — use a range of seasons for robustness
    fbs_teams = query_db("""
        SELECT DISTINCT "homeTeam" AS team FROM games WHERE "homeClassification" = 'fbs'
        UNION
        SELECT DISTINCT "awayTeam" AS team FROM games WHERE "awayClassification" = 'fbs'
    """)
    fbs_set = set(fbs_teams["team"])

    # Incoming: only count FBS→FBS transfers (both origin and destination must be FBS)
    fbs_incoming = df[df["destination"].isin(fbs_set) & df["origin"].isin(fbs_set)]
    incoming = (
        fbs_incoming.groupby("destination")["weighted_stars"].sum()
        .reset_index()
        .rename(columns={"destination": "team", "weighted_stars": "stars_in"})
    )

    # Outgoing: all departures from FBS origin teams
    fbs_outgoing = df[df["origin"].isin(fbs_set)]
    outgoing = (
        fbs_outgoing.groupby("origin")["weighted_stars"].sum()
        .reset_index()
        .rename(columns={"origin": "team", "weighted_stars": "stars_out"})
    )

    net = incoming.merge(outgoing, on="team", how="outer").fillna(0)
    net["net_portal_score"] = net["stars_in"] - net["stars_out"]
    net["season"] = year

    save_to_db(net[["season", "team", "stars_in", "stars_out", "net_portal_score"]], "portal_net_ratings")
    return net