"""Standalone training script for LightGBM win probability model v2.

Key improvements over v1 (23 features):
  - Removes 9 team_stats features (zero at inference — season aggregates not
    available before a game is played, so the model learned patterns it cannot
    replicate at prediction time).
  - Uses season-1 for ALL feature lookups (true preseason / prior-season data).
  - Adds portal_net_diff from portal_net_ratings.
  - Clips four outlier-prone features to prevent overconfident probabilities.
  - Recency weights: 2024=1.0, 2023=0.8, 2022=0.6, 2021=0.4

Output artifacts (models/saved/):
  win_prob_model_v2.pkl     — raw LightGBM (23 → 15 features)
  platt_scaler_v2.joblib    — CalibratedClassifierCV fitted on full training set
  feature_cols_v2.pkl       — ordered list of 15 feature column names

v1 artifacts are left untouched.
"""

import os
import sys

# Ensure repo root is importable when running as a script from any directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import lightgbm as lgb
import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, accuracy_score

from db.database import query_db

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAVED = os.path.join(os.path.dirname(__file__), "saved")

RECENCY_WEIGHTS = {2021: 0.4, 2022: 0.6, 2023: 0.8, 2024: 1.0}

# Clip bounds for outlier-prone features.
FEATURE_CLIPS = {
    "sp_overall_diff": (-25.0,  25.0),
    "elo_diff":        (-600.0, 600.0),
    "talent_diff":     (-400.0, 400.0),
    "rec_3yr_diff":    (-150.0, 150.0),
}

# Canonical feature order for v2. Any change here must be reflected in the
# saved feature_cols_v2.pkl artifact and in win_probability.py v2 functions.
FEATURE_COLS_V2 = [
    # SP+ (4)
    "sp_overall_diff",    # clipped ±25
    "sp_off_vs_def",
    "sp_def_vs_off",
    "sp_special_diff",
    
    # Recruiting & Talent (2)
    "rec_3yr_diff",       # clipped ±150
    "talent_diff",        # clipped ±400
    
    # Returning Production (2)
    "ret_ppa_diff",
    "ret_pct_diff",
    
    # Portal (1)
    "portal_net_diff",
    
    # Coaching (3)
    "coach_win_pct_diff",
    "home_new_coach",
    "away_new_coach",
    
    # Strength (1)
    "elo_diff",           # clipped ±600
    
    # Line Play (2) — NEW
    "offense_lineYards_diff",
    "defense_stuffRate_diff",
    
    # Game Context (2)
    "neutral_site",
    "home_field",
]

# These are the team_stats-derived features present in v1 that are removed in v2.
REMOVED_FEATURES_V1 = [
    "home_pointsPerGame", "away_pointsPerGame", "diff_pointsPerGame",
    "home_passingYards",  "away_passingYards",  "diff_passingYards",
    "home_rushingYards",  "away_rushingYards",  "diff_rushingYards",
]


# ---------------------------------------------------------------------------
# Data loaders (all features use season-1 lookup year)
# ---------------------------------------------------------------------------

def _load_sp():
    """SP+ ratings for all teams and years."""
    return query_db(
        'SELECT year, team, rating, offense_rating, defense_rating, "specialTeams_rating" '
        "FROM sp_ratings"
    )


def _load_recruiting():
    """3-year rolling average recruiting points, indexed by year.

    A team's rec_3yr_avg for year Y = mean of points in [Y-2, Y-1, Y].
    At inference time we look up year = season-1, giving us the class average
    for the three years leading up to the current season.
    """
    rec = query_db("SELECT year, team, points FROM recruiting_rankings")
    rec = rec.sort_values(["team", "year"])
    rec["rec_3yr_avg"] = (
        rec.groupby("team", sort=False)["points"]
        .transform(lambda s: s.rolling(3, min_periods=1).mean())
    )
    return rec[["year", "team", "rec_3yr_avg"]]


def _load_returning():
    """Returning production (totalPPA and percentPPA) by team and year."""
    return query_db(
        'SELECT season AS year, team, '
        '"totalPPA" AS ret_ppa_raw, "percentPPA" AS ret_pct '
        "FROM returning_production"
    )


def _load_coaches():
    """Coach records enriched with new-coach flag and cumulative career win%."""
    coaches = query_db(
        'SELECT school, year, "firstName", "lastName", wins, losses, games FROM coaches'
    )
    coaches = coaches.sort_values(["firstName", "lastName", "year"])

    # New coach: first season at this school
    min_yr = coaches.groupby(["school", "firstName", "lastName"])["year"].transform("min")
    coaches["is_new"] = (coaches["year"] == min_yr).astype(int)

    # Career win% — cumulative, +1 denominator to avoid division by zero
    coaches["career_wins"]  = coaches.groupby(["firstName", "lastName"])["wins"].cumsum()
    coaches["career_games"] = coaches.groupby(["firstName", "lastName"])["games"].cumsum()
    coaches["career_win_pct"] = (
        coaches["career_wins"] / (coaches["career_games"] + 1)
    ).fillna(0.5)

    return coaches[["school", "year", "is_new", "career_win_pct"]]


def _load_elo():
    """End-of-season Elo ratings by team and year."""
    return query_db("SELECT year, team, elo FROM elo_ratings")


def _load_talent():
    """Team talent composite scores by team and year."""
    return query_db("SELECT year, team, talent FROM talent")


def _load_portal():
    """Net portal score by team and season (re-aliased as year for consistency)."""
    return query_db(
        "SELECT season AS year, team, net_portal_score FROM portal_net_ratings"
    )


def _load_line_play(season):
    """Load line play metrics from advanced_stats for season-1."""
    return query_db(f"""
        SELECT team, season,
               "offense_lineYards" as "offense_lineYards",
               "defense_stuffRate" as "defense_stuffRate"
        FROM advanced_stats
        WHERE season = {season}
    """)


# ---------------------------------------------------------------------------
# Scalar lookup helper
# ---------------------------------------------------------------------------

def _scalar(df, team_col, year_col, val_col, team, year, default=None):
    """Return a single float value from a reference DataFrame.

    Args:
        df: Reference DataFrame.
        team_col: Column name for team identifier.
        year_col: Column name for year/season identifier.
        val_col: Column name for the value to extract.
        team: Team name to look up.
        year: Year to look up.
        default: Value to return when no row is found or value is null.

    Returns:
        float or default.
    """
    row = df[(df[team_col] == team) & (df[year_col] == year)]
    if row.empty:
        return default
    v = row.iloc[0][val_col]
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return default
    return float(v)


def _sp_vals(sp, team, year):
    """Return (overall, offense, defense, special_teams) SP+ ratings or Nones."""
    row = sp[(sp["team"] == team) & (sp["year"] == year)]
    if row.empty:
        return None, None, None, None
    r = row.iloc[0]
    return (
        float(r["rating"]          or 0),
        float(r["offense_rating"]  or 0),
        float(r["defense_rating"]  or 0),
        float(r["specialTeams_rating"] or 0),
    )


# ---------------------------------------------------------------------------
# Feature builder (v2) — all lookups use season-1
# ---------------------------------------------------------------------------

def _build_features_v2(
    home_team, away_team, season,
    sp, rec, ret, coa, elo, talent, portal, line,
    neutral_site=False,
):
    """Build the 17 v2 features for a single game.

    All reference tables are looked up at year = season - 1. This ensures
    only preseason / prior-season information is used, which is also the
    information available at inference time.

    SP+ is required for both teams. If either is missing the game is skipped
    (returns None). All other features fall back to 0.0 when data is absent.

    Args:
        home_team: Home team name (as it appears in the DB).
        away_team: Away team name.
        season: Game season year (e.g. 2024). Lookups use season-1.
        sp, rec, ret, coa, elo, talent, portal, line: Pre-loaded reference DataFrames.
        neutral_site: True for neutral-site games.

    Returns:
        dict of feature name → float, or None if SP+ is missing for either team.
    """
    ly = season - 1  # lookup year

    h_sp, h_sp_off, h_sp_def, h_sp_st = _sp_vals(sp, home_team, ly)
    a_sp, a_sp_off, a_sp_def, a_sp_st = _sp_vals(sp, away_team, ly)

    # SP+ is the strongest signal — drop the game if missing for either team
    if h_sp is None or a_sp is None:
        return None

    f = {}

    # SP+ matchup features
    f["sp_overall_diff"] = h_sp - a_sp
    f["sp_off_vs_def"]   = h_sp_off - a_sp_def  # home off vs away def
    f["sp_def_vs_off"]   = a_sp_off - h_sp_def  # away off vs home def
    f["sp_special_diff"] = h_sp_st - a_sp_st

    # 3-year rolling recruiting average differential
    h_rec = _scalar(rec, "team", "year", "rec_3yr_avg", home_team, ly, default=0.0)
    a_rec = _scalar(rec, "team", "year", "rec_3yr_avg", away_team, ly, default=0.0)
    f["rec_3yr_diff"] = h_rec - a_rec

    # Talent composite differential
    h_tal = _scalar(talent, "team", "year", "talent", home_team, ly, default=0.0)
    a_tal = _scalar(talent, "team", "year", "talent", away_team, ly, default=0.0)
    f["talent_diff"] = h_tal - a_tal

    # Returning production differentials
    h_ppa = _scalar(ret, "team", "year", "ret_ppa_raw", home_team, ly, default=0.0)
    a_ppa = _scalar(ret, "team", "year", "ret_ppa_raw", away_team, ly, default=0.0)
    h_pct = _scalar(ret, "team", "year", "ret_pct",     home_team, ly, default=0.0)
    a_pct = _scalar(ret, "team", "year", "ret_pct",     away_team, ly, default=0.0)
    f["ret_ppa_diff"] = h_ppa - a_ppa
    f["ret_pct_diff"] = h_pct - a_pct

    # Portal net score differential
    h_por = _scalar(portal, "team", "year", "net_portal_score", home_team, ly, default=0.0)
    a_por = _scalar(portal, "team", "year", "net_portal_score", away_team, ly, default=0.0)
    f["portal_net_diff"] = h_por - a_por

    # Coaching signals
    h_new  = _scalar(coa, "school", "year", "is_new",         home_team, ly, default=0)
    a_new  = _scalar(coa, "school", "year", "is_new",         away_team, ly, default=0)
    h_wpct = _scalar(coa, "school", "year", "career_win_pct", home_team, ly, default=0.5)
    a_wpct = _scalar(coa, "school", "year", "career_win_pct", away_team, ly, default=0.5)
    f["home_new_coach"]     = int(h_new or 0)
    f["away_new_coach"]     = int(a_new or 0)
    f["coach_win_pct_diff"] = h_wpct - a_wpct

    # Elo differential
    h_elo = _scalar(elo, "team", "year", "elo", home_team, ly, default=0.0)
    a_elo = _scalar(elo, "team", "year", "elo", away_team, ly, default=0.0)
    f["elo_diff"] = h_elo - a_elo

    # Line Play features (using neutral defaults from training data)
    h_ly = _scalar(line, "team", "season", "offense_lineYards", home_team, ly, default=None)
    a_ly = _scalar(line, "team", "season", "offense_lineYards", away_team, ly, default=None)
    if h_ly is not None and a_ly is not None:
        f["offense_lineYards_diff"] = h_ly - a_ly
    elif h_ly is not None:
        f["offense_lineYards_diff"] = h_ly - 3.04
    elif a_ly is not None:
        f["offense_lineYards_diff"] = 3.04 - a_ly
    else:
        f["offense_lineYards_diff"] = 0.009

    h_sr = _scalar(line, "team", "season", "defense_stuffRate", home_team, ly, default=None)
    a_sr = _scalar(line, "team", "season", "defense_stuffRate", away_team, ly, default=None)
    if h_sr is not None and a_sr is not None:
        f["defense_stuffRate_diff"] = h_sr - a_sr
    elif h_sr is not None:
        f["defense_stuffRate_diff"] = h_sr - 0.179
    elif a_sr is not None:
        f["defense_stuffRate_diff"] = 0.179 - a_sr
    else:
        f["defense_stuffRate_diff"] = 0.0016

    # Home field
    f["neutral_site"] = 1 if neutral_site else 0
    f["home_field"]   = 0 if neutral_site else 1

    return f


def _apply_clips(df: pd.DataFrame) -> pd.DataFrame:
    """Clip outlier-prone features to prevent extreme win probability outputs."""
    for col, (lo, hi) in FEATURE_CLIPS.items():
        if col in df.columns:
            df[col] = df[col].clip(lo, hi)
    return df


# ---------------------------------------------------------------------------
# Training data builders
# ---------------------------------------------------------------------------

def _load_all_tables():
    """Load all six reference tables once and return them as a tuple."""
    return (
        _load_sp(),
        _load_recruiting(),
        _load_returning(),
        _load_coaches(),
        _load_elo(),
        _load_talent(),
        _load_portal(),
    )


def build_training_data_v2():
    """Load FBS games 2021-2024 and build the 17-feature v2 training set.

    Only games that appear in betting_lines are included (FBS-only signal).
    Rows where more than 3 features are null are dropped.

    Returns:
        Tuple of (DataFrame[features + home_win + season], sample_weights ndarray).
    """
    games = query_db("""
        SELECT DISTINCT ON (g.id)
               g.id, g."homeTeam", g."awayTeam",
               g."homePoints", g."awayPoints",
               g.season, g."neutralSite"
        FROM games g
        INNER JOIN betting_lines bl ON bl.game_id::bigint = g.id::bigint
        WHERE g."homePoints"  IS NOT NULL
          AND g."awayPoints"  IS NOT NULL
          AND g."homeClassification" = 'fbs'
          AND g."awayClassification" = 'fbs'
          AND g.season BETWEEN 2021 AND 2024
        ORDER BY g.id
    """)

    sp, rec, ret, coa, elo, talent, portal = _load_all_tables()
    
    line_cache = {}

    records, sample_weights = [], []

    for _, game in games.iterrows():
        season  = int(game["season"])
        neutral = bool(game["neutralSite"])
        
        if season not in line_cache:
            line_cache[season] = _load_line_play(season - 1)

        features = _build_features_v2(
            game["homeTeam"], game["awayTeam"], season,
            sp, rec, ret, coa, elo, talent, portal, line_cache[season],
            neutral_site=neutral,
        )
        if features is None:
            continue

        null_count = sum(1 for v in features.values() if v is None)
        if null_count > 3:
            continue

        features["home_win"] = 1 if game["homePoints"] > game["awayPoints"] else 0
        features["season"]   = season
        records.append(features)
        sample_weights.append(RECENCY_WEIGHTS.get(season, 1.0))

    df = pd.DataFrame(records).fillna(0)
    df = _apply_clips(df)
    return df, np.array(sample_weights)


def build_holdout_v2():
    """Load completed 2025 FBS games and build v2 features for holdout evaluation.

    Returns:
        Tuple of (DataFrame[features + home_win + homeTeam + awayTeam], empty ndarray).
        homeTeam/awayTeam columns are preserved so v1 can be evaluated on the
        same games.
    """
    games = query_db("""
        SELECT DISTINCT ON (g.id)
               g.id, g."homeTeam", g."awayTeam",
               g."homePoints", g."awayPoints",
               g.season, g."neutralSite"
        FROM games g
        INNER JOIN betting_lines bl ON bl.game_id::bigint = g.id::bigint
        WHERE g."homePoints"  IS NOT NULL
          AND g."awayPoints"  IS NOT NULL
          AND g."homeClassification" = 'fbs'
          AND g."awayClassification" = 'fbs'
          AND g.season = 2025
        ORDER BY g.id
    """)

    if games.empty:
        return pd.DataFrame(), np.array([])

    sp, rec, ret, coa, elo, talent, portal = _load_all_tables()
    
    line_cache = {}

    records = []
    for _, game in games.iterrows():
        season  = int(game["season"])
        neutral = bool(game["neutralSite"])
        
        if season not in line_cache:
            line_cache[season] = _load_line_play(season - 1)

        features = _build_features_v2(
            game["homeTeam"], game["awayTeam"], season,
            sp, rec, ret, coa, elo, talent, portal, line_cache[season],
            neutral_site=neutral,
        )
        if features is None:
            continue

        features["home_win"]  = 1 if game["homePoints"] > game["awayPoints"] else 0
        features["season"]    = season
        features["homeTeam"]  = game["homeTeam"]
        features["awayTeam"]  = game["awayTeam"]
        records.append(features)

    if not records:
        return pd.DataFrame(), np.array([])

    df = pd.DataFrame(records).fillna(0)
    df = _apply_clips(df)
    return df, np.array([])


# ---------------------------------------------------------------------------
# Main training routine
# ---------------------------------------------------------------------------

def _evaluate_v1_on_holdout(holdout_df: pd.DataFrame):
    """Run v1 inference on the holdout game set and return (accuracy, brier, n).

    Returns (None, None, 0) if v1 artifacts are missing or inference fails.
    """
    v1_model_path   = os.path.join(SAVED, "win_prob_model.pkl")
    v1_cols_path    = os.path.join(SAVED, "feature_cols.pkl")
    v1_scaler_path  = os.path.join(SAVED, "platt_scaler.joblib")

    if not all(os.path.exists(p) for p in [v1_model_path, v1_cols_path, v1_scaler_path]):
        return None, None, 0

    try:
        from models.win_probability import (
            build_team_profiles,
            _load_sp        as _v1_sp,
            _load_recruiting as _v1_rec,
            _load_returning  as _v1_ret,
            _load_coaches    as _v1_coa,
            _load_elo        as _v1_elo,
            _load_talent     as _v1_tal,
            _build_features  as _v1_build,
        )

        v1_model  = joblib.load(v1_model_path)
        v1_cols   = joblib.load(v1_cols_path)
        v1_scaler = joblib.load(v1_scaler_path)

        profiles = build_team_profiles()
        key_stats = ["pointsPerGame", "passingYards", "rushingYards", "turnovers", "fumblesLost"]
        avail = [s for s in key_stats if s in profiles.columns]
        profiles = profiles[["team", "season"] + avail].fillna(0)

        sp = _v1_sp(); rec = _v1_rec(); ret = _v1_ret()
        coa = _v1_coa(); elo = _v1_elo(); tal = _v1_tal()

        rows, y_vals = [], []
        for _, row in holdout_df.iterrows():
            feats = _v1_build(
                row["homeTeam"], row["awayTeam"], int(row["season"]),
                profiles, sp, rec, ret, coa, avail, elo, tal,
                neutral_site=bool(row.get("neutral_site", 0)),
            )
            if feats is None:
                continue
            rows.append(feats)
            y_vals.append(int(row["home_win"]))

        if not rows:
            return None, None, 0

        X_v1     = pd.DataFrame(rows)[v1_cols]
        raw_v1   = v1_model.predict_proba(X_v1)[:, 1]
        cal_fn   = v1_scaler.calibrated_classifiers_[0].calibrators[0]
        cal_v1   = cal_fn.predict(raw_v1)
        y_v1     = np.array(y_vals)

        acc   = accuracy_score(y_v1, (cal_v1 >= 0.5).astype(int))
        brier = brier_score_loss(y_v1, cal_v1)
        return acc, brier, len(y_v1)

    except Exception as exc:
        print(f"  [v1 comparison skipped: {exc}]")
        return None, None, 0


def train_v2():
    """Train the v2 model, evaluate, print report, and save artifacts.

    Training split:
      - LightGBM: 2021–2024 games with recency weights.
      - Calibration: Isotonic regression with 5-fold CV on full 2021-2024 training set.
      - Holdout: 2025 completed games.

    Returns:
        Tuple of (raw_model, calibrated_model, feature_cols).
    """
    sep = "=" * 55
    print(sep)
    print("=== V2 RETRAIN REPORT ===")
    print(sep)

    # ------------------------------------------------------------------ #
    # 1. Training data
    # ------------------------------------------------------------------ #
    print("\nBuilding training data (2021-2024)...")
    train_df, weights = build_training_data_v2()
    
    X_train = train_df[FEATURE_COLS_V2].fillna(0)
    y_train = train_df["home_win"]
    w_train = weights

    print(f"Total training games (2021-2024): {len(train_df)}")
    print(f"Features: {len(FEATURE_COLS_V2)}")

    # ------------------------------------------------------------------ #
    # 2. Train LightGBM & Isotonic Calibration
    # ------------------------------------------------------------------ #
    print("Training raw LightGBM...")
    lgbm_model = lgb.LGBMClassifier(
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
    lgbm_model.fit(X_train, y_train, sample_weight=w_train)

    print("Fitting Isotonic calibration (5-fold CV)...")
    calibrated_model = CalibratedClassifierCV(
        lgbm_model,
        method='isotonic',
        cv=5
    )
    calibrated_model.fit(X_train, y_train, sample_weight=w_train)

    # ------------------------------------------------------------------ #
    # 3. Holdout evaluation
    # ------------------------------------------------------------------ #
    print("Building 2025 holdout...")
    holdout_df, _ = build_holdout_v2()

    if holdout_df.empty:
        print("No 2025 holdout games found — skipping evaluation.")
        n_test = 0
        v2_acc = v2_brier = None
    else:
        X_test = holdout_df[FEATURE_COLS_V2].fillna(0)
        y_test = holdout_df["home_win"].values
        n_test = len(X_test)

        # Calibrated output
        cal_probs_v2 = calibrated_model.predict_proba(X_test)[:, 1]

        v2_acc   = accuracy_score(y_test, (cal_probs_v2 >= 0.5).astype(int))
        v2_brier = brier_score_loss(y_test, cal_probs_v2)

    # ------------------------------------------------------------------ #
    # 4. v1 comparison on the same holdout games
    # ------------------------------------------------------------------ #
    v1_acc, v1_brier, n_v1 = _evaluate_v1_on_holdout(holdout_df) if not holdout_df.empty else (None, None, 0)

    # ------------------------------------------------------------------ #
    # 5. Print report
    # ------------------------------------------------------------------ #
    print("\n--- ACCURACY ---")
    if v1_acc is not None:
        print(f"V1 (23 features, Platt):     {v1_acc:.2%}")
    print(f"V2 (17 features, isotonic):  {v2_acc:.2%}")

    print("\n--- BRIER SCORE ---")
    if v1_brier is not None:
        print(f"V1: {v1_brier:.4f}")
    print(f"V2: {v2_brier:.4f}")

    if v2_brier is not None:
        print("\n--- CALIBRATION (2025 holdout) ---")
        edges = [0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 1.0]
        print(f"  {'bucket':>7}  {'v2_pred':>9}  {'v2_actual':>9}  {'count':>5}")
        for lo, hi in zip(edges[:-1], edges[1:]):
            mask = (cal_probs_v2 >= lo) & (cal_probs_v2 < hi)
            n_bin = int(mask.sum())
            if n_bin == 0: continue
            pred   = float(cal_probs_v2[mask].mean())
            actual = float(y_test[mask].mean())
            print(f"  {lo:.1f}–{hi:.1f}  {pred:>9.3f}  {actual:>8.1%}  {n_bin:>5}")

        print("\n--- EXTREME PREDICTIONS ---")
        high_v2 = cal_probs_v2 >= 0.90
        n_high  = int(high_v2.sum())
        wr_high = float(y_test[high_v2].mean()) if n_high > 0 else 0.0
        print(f"V2 games above 90%: {n_high} ({wr_high:.1%} actual win rate)")
        
        low_v2 = cal_probs_v2 <= 0.10
        n_low  = int(low_v2.sum())
        wr_low = float(y_test[low_v2].mean()) if n_low > 0 else 0.0
        print(f"V2 games below 10%: {n_low} ({wr_low:.1%} actual win rate)")

    print("\n--- FEATURE IMPORTANCE (top 10) ---")
    importances = lgbm_model.feature_importances_
    feat_imp = sorted(zip(FEATURE_COLS_V2, importances), key=lambda x: x[1], reverse=True)
    for f_name, imp in feat_imp[:10]:
        print(f"{f_name:<25}: {imp}")

    # ------------------------------------------------------------------ #
    # 6. Save artifacts
    # ------------------------------------------------------------------ #
    os.makedirs(SAVED, exist_ok=True)
    joblib.dump(lgbm_model,      os.path.join(SAVED, "win_prob_model_v2.pkl"))
    joblib.dump(calibrated_model, os.path.join(SAVED, "platt_scaler_v2.joblib"))
    joblib.dump(FEATURE_COLS_V2, os.path.join(SAVED, "feature_cols_v2.pkl"))

    # Mirror artifacts to backend/models/saved/
    _backend_saved = os.path.join(os.path.dirname(__file__), "..", "backend", "models", "saved")
    os.makedirs(_backend_saved, exist_ok=True)
    import shutil
    for fname in ("win_prob_model_v2.pkl", "platt_scaler_v2.joblib", "feature_cols_v2.pkl"):
        shutil.copy2(os.path.join(SAVED, fname), os.path.join(_backend_saved, fname))

    print("\nArtifacts saved.")
    return lgbm_model, calibrated_model, FEATURE_COLS_V2


if __name__ == "__main__":
    train_v2()
