import pandas as pd
import numpy as np
import lightgbm as lgb
from db.database import query_db
import joblib
import os

RECENCY_WEIGHTS = {2021: 0.2, 2022: 0.4, 2023: 0.6, 2024: 0.8, 2025: 1.0}

# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def build_team_profiles():
    """Pivot team_stats into per-team/season columns. Kept for app.py compatibility."""
    stats = query_db('SELECT season, team, "statName", "statValue" FROM team_stats')
    pivot = stats.pivot_table(
        index=["team", "season"],
        columns="statName",
        values="statValue"
    ).reset_index()
    return pivot


def _load_sp():
    return query_db(
        'SELECT year, team, rating, offense_rating, defense_rating, "specialTeams_rating" '
        "FROM sp_ratings"
    )


def _load_recruiting():
    rec = query_db("SELECT year, team, points FROM recruiting_rankings")
    rec = rec.sort_values(["team", "year"])
    rec["rec_3yr_avg"] = (
        rec.groupby("team", sort=False)["points"]
        .transform(lambda s: s.rolling(3, min_periods=1).mean())
    )
    return rec[["year", "team", "rec_3yr_avg"]]


def _load_returning():
    return query_db(
        'SELECT season AS year, team, "totalPPA" AS "ret_totalPPA", "percentPPA" AS "ret_percentPPA" '
        "FROM returning_production"
    )


def _load_coaches():
    coaches = query_db(
        'SELECT school, year, "firstName", "lastName", wins, losses, games FROM coaches'
    )
    coaches = coaches.sort_values(["firstName", "lastName", "year"])

    # New coach: first year at this school
    min_yr = coaches.groupby(["school", "firstName", "lastName"])["year"].transform("min")
    coaches["is_new"] = (coaches["year"] == min_yr).astype(int)

    # Career win% — cumulative across all schools up to this season
    coaches["career_wins"]  = coaches.groupby(["firstName", "lastName"])["wins"].cumsum()
    coaches["career_games"] = coaches.groupby(["firstName", "lastName"])["games"].cumsum()
    coaches["career_win_pct"] = (
        coaches["career_wins"] / coaches["career_games"].replace(0, np.nan)
    ).fillna(0.5)

    return coaches[["school", "year", "is_new", "career_win_pct"]]


def _load_elo():
    """Load end-of-season Elo ratings for all teams and years."""
    return query_db("SELECT year, team, elo FROM elo_ratings")


def _load_talent():
    """Load team talent composite scores for all teams and years."""
    return query_db("SELECT year, team, talent FROM talent")


# ---------------------------------------------------------------------------
# Per-team feature helpers
# ---------------------------------------------------------------------------

def _sp_vals(sp, team, year):
    row = sp[(sp["team"] == team) & (sp["year"] == year)]
    if row.empty:
        return 0.0, 0.0, 0.0, 0.0
    r = row.iloc[0]
    return (
        float(r["rating"] or 0),
        float(r["offense_rating"] or 0),
        float(r["defense_rating"] or 0),
        float(r["specialTeams_rating"] or 0),
    )


def _rec_val(rec, team, year):
    row = rec[(rec["team"] == team) & (rec["year"] == year)]
    return float(row.iloc[0]["rec_3yr_avg"] or 0) if not row.empty else 0.0


def _ret_vals(ret, team, year):
    row = ret[(ret["team"] == team) & (ret["year"] == year)]
    if row.empty:
        return 0.0, 0.0
    r = row.iloc[0]
    return float(r["ret_totalPPA"] or 0), float(r["ret_percentPPA"] or 0)


def _coach_vals(coa, team, year):
    row = coa[(coa["school"] == team) & (coa["year"] == year)]
    if row.empty:
        return 0, 0.5
    r = row.iloc[0]
    return int(r["is_new"]), float(r["career_win_pct"] or 0.5)


def _elo_val(elo, team, year):
    """Return a team's Elo rating for a given year, or 0.0 if missing."""
    row = elo[(elo["team"] == team) & (elo["year"] == year)]
    return float(row.iloc[0]["elo"] or 0) if not row.empty else 0.0


def _talent_val(talent, team, year):
    """Return a team's talent composite score for a given year, or 0.0 if missing."""
    row = talent[(talent["team"] == team) & (talent["year"] == year)]
    return float(row.iloc[0]["talent"] or 0) if not row.empty else 0.0


# ---------------------------------------------------------------------------
# Feature builder (shared by training and prediction)
# ---------------------------------------------------------------------------

def _build_features(home_team, away_team, season, profiles, sp, rec, ret, coa, available_stats, elo, talent, neutral_site=False):
    home_prof = profiles[(profiles["team"] == home_team) & (profiles["season"] == season)]
    away_prof = profiles[(profiles["team"] == away_team) & (profiles["season"] == season)]
    if home_prof.empty or away_prof.empty:
        return None
    hp, ap = home_prof.iloc[0], away_prof.iloc[0]

    f = {}

    # Legacy team_stats differentials
    for stat in available_stats:
        hv = float(hp.get(stat, 0) or 0)
        av = float(ap.get(stat, 0) or 0)
        f[f"home_{stat}"] = hv
        f[f"away_{stat}"] = av
        f[f"diff_{stat}"] = hv - av

    # SP+ — offense vs defense matchup + overall + special teams
    h_sp, h_sp_off, h_sp_def, h_sp_st = _sp_vals(sp, home_team, season)
    a_sp, a_sp_off, a_sp_def, a_sp_st = _sp_vals(sp, away_team, season)
    f["sp_overall_diff"] = h_sp - a_sp
    f["sp_off_vs_def"]   = h_sp_off - a_sp_def   # home offense vs away defense
    f["sp_def_vs_off"]   = a_sp_off - h_sp_def   # away offense vs home defense (lower = better for home)
    f["sp_special_diff"] = h_sp_st - a_sp_st

    # 3-year rolling recruiting average differential
    f["rec_3yr_diff"] = _rec_val(rec, home_team, season) - _rec_val(rec, away_team, season)

    # Returning production differential
    h_ppa, h_pct = _ret_vals(ret, home_team, season)
    a_ppa, a_pct = _ret_vals(ret, away_team, season)
    f["ret_ppa_diff"] = h_ppa - a_ppa
    f["ret_pct_diff"] = h_pct - a_pct

    # Coaching: new coach flags + career win% differential
    h_new, h_wpct = _coach_vals(coa, home_team, season)
    a_new, a_wpct = _coach_vals(coa, away_team, season)
    f["home_new_coach"]     = h_new
    f["away_new_coach"]     = a_new
    f["coach_win_pct_diff"] = h_wpct - a_wpct

    # Elo differential
    f["elo_diff"] = _elo_val(elo, home_team, season) - _elo_val(elo, away_team, season)

    # Talent composite differential
    f["talent_diff"] = _talent_val(talent, home_team, season) - _talent_val(talent, away_team, season)

    # Home field advantage (zeroed out for neutral-site games)
    f["neutral_site"] = 1 if neutral_site else 0
    f["home_field"]   = 0 if neutral_site else 1

    return f


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def build_training_data():
    games = query_db("""
        SELECT id, "homeTeam", "awayTeam", "homePoints", "awayPoints", season, "neutralSite"
        FROM games
        WHERE "homePoints" IS NOT NULL AND "awayPoints" IS NOT NULL
          AND "homeClassification" = 'fbs' AND "awayClassification" = 'fbs'
    """)

    # Join pregame spread from pregame_wp on gameId
    wp = query_db('SELECT "gameId", spread FROM pregame_wp')
    games = games.merge(wp, left_on="id", right_on="gameId", how="left")

    profiles = build_team_profiles()
    key_stats = ["pointsPerGame", "passingYards", "rushingYards", "turnovers", "fumblesLost"]
    available_stats = [s for s in key_stats if s in profiles.columns]
    profiles = profiles[["team", "season"] + available_stats].fillna(0)

    sp     = _load_sp()
    rec    = _load_recruiting()
    ret    = _load_returning()
    coa    = _load_coaches()
    elo    = _load_elo()
    talent = _load_talent()

    records, sample_weights = [], []

    for _, game in games.iterrows():
        season = int(game["season"])
        neutral = bool(game["neutralSite"])
        features = _build_features(
            game["homeTeam"], game["awayTeam"], season,
            profiles, sp, rec, ret, coa, available_stats, elo, talent, neutral
        )
        if features is None:
            continue
        features["spread_diff"] = float(game["spread"]) if pd.notna(game.get("spread")) else 0.0
        features["home_win"]    = 1 if game["homePoints"] > game["awayPoints"] else 0
        features["season"]      = season
        records.append(features)
        sample_weights.append(RECENCY_WEIGHTS.get(season, 1.0))

    return pd.DataFrame(records), np.array(sample_weights)


def train_model():
    print("Building training data...")
    df, weights = build_training_data()

    feature_cols = [c for c in df.columns if c not in ("home_win", "season")]

    train_mask = df["season"] < 2025
    test_mask  = df["season"] == 2025

    X_train = df.loc[train_mask, feature_cols]
    y_train = df.loc[train_mask, "home_win"]
    w_train = weights[train_mask.values]

    X_test = df.loc[test_mask, feature_cols]
    y_test = df.loc[test_mask, "home_win"]

    model = lgb.LGBMClassifier(
        n_estimators=500,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=20,
        reg_alpha=0.1,
        reg_lambda=0.1,
        subsample=0.8,
        random_state=42,
        verbose=-1,
    )
    model.fit(X_train, y_train, sample_weight=w_train)

    train_acc = model.score(X_train, y_train)
    print(f"Train accuracy (2021-2024): {train_acc:.2%}  ({len(X_train)} games)")

    if not X_test.empty:
        test_acc = model.score(X_test, y_test)
        print(f"Holdout accuracy  (2025):   {test_acc:.2%}  ({len(X_test)} games)")
    else:
        print("No 2025 games with scores for holdout evaluation.")

    os.makedirs("models/saved", exist_ok=True)
    joblib.dump(model,        "models/saved/win_prob_model.pkl")
    joblib.dump(feature_cols, "models/saved/feature_cols.pkl")
    print("Model saved.")

    return model, feature_cols


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

# Logistic calibration for composite-based 2026 predictions.
# k=0.06, HOME_FIELD=4.0 → equal teams at home ≈ 56%, 20-pt edge ≈ 81%.
_COMPOSITE_K          = 0.06
_COMPOSITE_HOME_FIELD = 4.0

def _predict_from_preseason_composite(home_team: str, away_team: str, table: str) -> float | str:
    df = query_db(f"SELECT team, composite_100 FROM {table}")
    scores = dict(zip(df["team"], df["composite_100"]))
    h = scores.get(home_team)
    a = scores.get(away_team)
    if h is None:
        return f"No preseason composite data found for {home_team}"
    if a is None:
        return f"No preseason composite data found for {away_team}"
    diff = (h + _COMPOSITE_HOME_FIELD) - a
    prob = 1.0 / (1.0 + np.exp(-_COMPOSITE_K * diff))
    return round(float(prob), 4)


def predict_win_probability(home_team: str, away_team: str, season: int = 2024):
    # 2026: no in-season data yet — use preseason composite ratings
    if season == 2026:
        return _predict_from_preseason_composite(home_team, away_team, "preseason_2026")

    model        = joblib.load("models/saved/win_prob_model.pkl")
    feature_cols = joblib.load("models/saved/feature_cols.pkl")

    profiles = build_team_profiles()
    key_stats = ["pointsPerGame", "passingYards", "rushingYards", "turnovers", "fumblesLost"]
    available_stats = [s for s in key_stats if s in profiles.columns]
    profiles = profiles[["team", "season"] + available_stats].fillna(0)

    sp     = _load_sp()
    rec    = _load_recruiting()
    ret    = _load_returning()
    coa    = _load_coaches()
    elo    = _load_elo()
    talent = _load_talent()

    features = _build_features(
        home_team, away_team, season,
        profiles, sp, rec, ret, coa, available_stats, elo, talent, neutral_site=False
    )

    if features is None:
        home_check = profiles[(profiles["team"] == home_team) & (profiles["season"] == season)]
        if home_check.empty:
            return f"No data found for {home_team} in {season}"
        return f"No data found for {away_team} in {season}"

    X = pd.DataFrame([features])[feature_cols]
    prob = model.predict_proba(X)[0][1]
    return round(float(prob), 4)


if __name__ == "__main__":
    train_model()
