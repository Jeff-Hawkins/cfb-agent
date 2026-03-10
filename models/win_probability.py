import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from db.database import query_db
import joblib
import os

def build_team_profiles():
    stats = query_db("SELECT * FROM team_stats")
    
    pivot = stats.pivot_table(
        index=["team", "season"],
        columns="statName",
        values="statValue"
    ).reset_index()
    
    return pivot

def build_training_data():
    games = query_db("""
        SELECT homeTeam, awayTeam, homePoints, awayPoints, season
        FROM games
        WHERE homePoints IS NOT NULL 
        AND awayPoints IS NOT NULL
        AND homeClassification = 'fbs'
        AND awayClassification = 'fbs'
    """)
    
    profiles = build_team_profiles()
    
    key_stats = [
        "pointsPerGame", "passingYards", "rushingYards",
        "turnovers", "fumblesLost"
    ]
    
    available_stats = [s for s in key_stats if s in profiles.columns]
    
    cols = ["team", "season"] + available_stats
    profiles = profiles[cols].fillna(0)
    
    records = []
    for _, game in games.iterrows():
        home = profiles[
            (profiles["team"] == game["homeTeam"]) &
            (profiles["season"] == game["season"])
        ]
        away = profiles[
            (profiles["team"] == game["awayTeam"]) &
            (profiles["season"] == game["season"])
        ]
        
        if home.empty or away.empty:
            continue
        
        home = home.iloc[0]
        away = away.iloc[0]
        
        features = {}
        for stat in available_stats:
            features[f"home_{stat}"] = home.get(stat, 0)
            features[f"away_{stat}"] = away.get(stat, 0)
            features[f"diff_{stat}"] = home.get(stat, 0) - away.get(stat, 0)
        
        features["home_field"] = 1
        features["home_win"] = 1 if game["homePoints"] > game["awayPoints"] else 0
        
        records.append(features)
    
    return pd.DataFrame(records)

def train_model():
    print("Building training data...")
    df = build_training_data()
    
    feature_cols = [c for c in df.columns if c != "home_win"]
    X = df[feature_cols]
    y = df["home_win"]
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    model = LogisticRegression(max_iter=1000)
    model.fit(X_scaled, y)
    
    accuracy = model.score(X_scaled, y)
    print(f"Model accuracy: {accuracy:.2%}")
    print(f"Trained on {len(df)} games")
    
    os.makedirs("models/saved", exist_ok=True)
    joblib.dump(model, "models/saved/win_prob_model.pkl")
    joblib.dump(scaler, "models/saved/scaler.pkl")
    joblib.dump(feature_cols, "models/saved/feature_cols.pkl")
    print("Model saved.")
    
    return model, scaler, feature_cols

def predict_win_probability(home_team: str, away_team: str, season: int = 2024):
    model = joblib.load("models/saved/win_prob_model.pkl")
    scaler = joblib.load("models/saved/scaler.pkl")
    feature_cols = joblib.load("models/saved/feature_cols.pkl")
    
    profiles = build_team_profiles()
    available_stats = [c for c in feature_cols if c.startswith("diff_")]
    available_stats = [c.replace("diff_", "") for c in available_stats]
    
    home = profiles[
        (profiles["team"] == home_team) &
        (profiles["season"] == season)
    ]
    away = profiles[
        (profiles["team"] == away_team) &
        (profiles["season"] == season)
    ]
    
    if home.empty:
        return f"No data found for {home_team} in {season}"
    if away.empty:
        return f"No data found for {away_team} in {season}"
    
    home = home.iloc[0]
    away = away.iloc[0]
    
    features = {}
    for stat in available_stats:
        features[f"home_{stat}"] = home.get(stat, 0)
        features[f"away_{stat}"] = away.get(stat, 0)
        features[f"diff_{stat}"] = home.get(stat, 0) - away.get(stat, 0)
    features["home_field"] = 1
    
    X = pd.DataFrame([features])[feature_cols]
    X_scaled = scaler.transform(X)
    
    prob = model.predict_proba(X_scaled)[0][1]
    return round(prob, 4)

if __name__ == "__main__":
    train_model()