import pandas as pd
import numpy as np
import lightgbm as lgb
from db.database import query_db
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss
import joblib
import os

MODEL_VERSION = "2.0.0"
MODEL_VERSION_V2 = "2.2.0"  # 17 features, isotonic calibration, line play added

RECENCY_WEIGHTS = {2021: 0.2, 2022: 0.4, 2023: 0.6, 2024: 0.8, 2025: 1.0}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Constants used for implied spread calculations
MODEL_IMPLIED_SCALE = 28
_COMPOSITE_K = 0.08
_COMPOSITE_HOME_FIELD = 2.5

# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def build_team_profiles():
    """Pivot team_stats into per-team/season columns. Kept for app.py compatibility."""
    df = query_db("SELECT * FROM team_stats")
    # Pivot so each stat is a column, team/season is the index
    pivot = df.pivot(index=["team", "season"], columns="statName", values="statValue")
    return pivot.reset_index()


def _load_sp():
    return query_db('SELECT year, team, rating, offense_rating, defense_rating, "specialTeams_rating" FROM sp_ratings')


def _load_recruiting():
    rec = query_db("SELECT year, team, points FROM recruiting_rankings")
    rec = rec.sort_values(["team", "year"])
    rec["rec_3yr_avg"] = rec.groupby("team")["points"].transform(lambda s: s.rolling(3, min_periods=1).mean())
    return rec


def _load_returning():
    return query_db('SELECT season as year, team, "totalPPA" as "ret_totalPPA", "percentPPA" as "ret_percentPPA" FROM returning_production')


def _load_coaches():
    coa = query_db('SELECT school as team, year, "firstName", "lastName", wins, losses, games FROM coaches')
    coa = coa.sort_values(["team", "firstName", "lastName", "year"])
    coa["is_new"] = (coa.groupby(["team", "firstName", "lastName"]).cumcount() == 0).astype(int)
    coa["career_wins"] = coa.groupby(["firstName", "lastName"])["wins"].cumsum()
    coa["career_games"] = coa.groupby(["firstName", "lastName"])["games"].cumsum()
    coa["career_win_pct"] = (coa["career_wins"] / (coa["career_games"] + 1)).fillna(0.5)
    return coa


def _load_elo():
    return query_db("SELECT year, team, elo FROM elo_ratings")


def _load_talent():
    return query_db("SELECT year, team, talent FROM talent")


def _predict_from_preseason_composite(home_team, away_team, table_name="preseason_2026"):
    """Simple fallback for future seasons using preseason composite scores."""
    df = query_db(f"SELECT team, composite_100 FROM {table_name} WHERE team IN ('{home_team}', '{away_team}')")
    if len(df) < 2:
        return f"Preseason ratings missing for {home_team} or {away_team}"
    
    scores = dict(zip(df["team"], df["composite_100"]))
    h = scores[home_team]
    a = scores[away_team]
    
    # Logistic curve based on composite difference
    diff = (h + _COMPOSITE_HOME_FIELD) - a
    prob = round(float(1.0 / (1.0 + np.exp(-_COMPOSITE_K * diff))), 4)
    return {"win_prob": prob, "raw_win_prob": prob}


# ---------------------------------------------------------------------------
# Production Entry Points
# ---------------------------------------------------------------------------

def predict_win_probability(
    home_team: str,
    away_team: str,
    season: int = 2025,
    neutral_site: bool = False,
):
    """Production win probability endpoint (redirects to v2)."""
    return predict_win_probability_v2(home_team, away_team, season, neutral_site)


def predict_win_probability_batch(games: list, season: int) -> list:
    """Production batch win probability endpoint (redirects to v2)."""
    return predict_win_probability_batch_v2(games, season)


# ---------------------------------------------------------------------------
# v2 — 17-feature model (season-1 lookups, clipped outliers, portal added)
# ---------------------------------------------------------------------------

_V2_FEATURE_CLIPS = {
    "sp_overall_diff": (-25.0,  25.0),
    "elo_diff":        (-600.0, 600.0),
    "talent_diff":     (-400.0, 400.0),
    "rec_3yr_diff":    (-150.0, 150.0),
}


def _load_portal_v2():
    """Net portal score by team and season (re-aliased as year)."""
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


def _scalar_v2(df, team_col, year_col, val_col, team, year, default=None):
    """Generic scalar lookup from a reference DataFrame. Returns default when missing."""
    row = df[(df[team_col] == team) & (df[year_col] == year)]
    if row.empty:
        return default
    v = row.iloc[0][val_col]
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return default
    return float(v)


def _sp_vals_v2(sp, team, year):
    """Return (overall, offense, defense, special_teams) SP+ or Nones if missing."""
    row = sp[(sp["team"] == team) & (sp["year"] == year)]
    if row.empty:
        return None, None, None, None
    r = row.iloc[0]
    return (
        float(r["rating"]              or 0),
        float(r["offense_rating"]      or 0),
        float(r["defense_rating"]      or 0),
        float(r["specialTeams_rating"] or 0),
    )


def _build_features_v2(
    home_team, away_team, season,
    sp, rec, ret, coa, elo, talent, portal, line,
    neutral_site=False,
):
    """Build the 17 v2 features for a single game.

    All reference tables are looked up at year = season - 1 (prior-season data),
    matching the information available before any game is played.

    Returns dict of feature name → float, or None if SP+ is missing for either team.
    """
    ly = season - 1  # lookup year

    h_sp, h_sp_off, h_sp_def, h_sp_st = _sp_vals_v2(sp, home_team, ly)
    a_sp, a_sp_off, a_sp_def, a_sp_st = _sp_vals_v2(sp, away_team, ly)
    if h_sp is None or a_sp is None:
        return None

    f = {}
    f["sp_overall_diff"] = h_sp - a_sp
    f["sp_off_vs_def"]   = h_sp_off - a_sp_def
    f["sp_def_vs_off"]   = a_sp_off - h_sp_def
    f["sp_special_diff"] = h_sp_st - a_sp_st

    h_rec = _scalar_v2(rec, "team", "year", "rec_3yr_avg", home_team, ly, default=0.0)
    a_rec = _scalar_v2(rec, "team", "year", "rec_3yr_avg", away_team, ly, default=0.0)
    f["rec_3yr_diff"] = h_rec - a_rec

    h_tal = _scalar_v2(talent, "team", "year", "talent", home_team, ly, default=0.0)
    a_tal = _scalar_v2(talent, "team", "year", "talent", away_team, ly, default=0.0)
    f["talent_diff"] = h_tal - a_tal

    h_ppa = _scalar_v2(ret, "team", "year", "ret_totalPPA",   home_team, ly, default=0.0)
    a_ppa = _scalar_v2(ret, "team", "year", "ret_totalPPA",   away_team, ly, default=0.0)
    h_pct = _scalar_v2(ret, "team", "year", "ret_percentPPA", home_team, ly, default=0.0)
    a_pct = _scalar_v2(ret, "team", "year", "ret_percentPPA", away_team, ly, default=0.0)
    f["ret_ppa_diff"] = h_ppa - a_ppa
    f["ret_pct_diff"] = h_pct - a_pct

    h_por = _scalar_v2(portal, "team", "year", "net_portal_score", home_team, ly, default=0.0)
    a_por = _scalar_v2(portal, "team", "year", "net_portal_score", away_team, ly, default=0.0)
    f["portal_net_diff"] = h_por - a_por

    h_new  = _scalar_v2(coa, "team", "year", "is_new",         home_team, ly, default=0)
    a_new  = _scalar_v2(coa, "team", "year", "is_new",         away_team, ly, default=0)
    h_wpct = _scalar_v2(coa, "team", "year", "career_win_pct", home_team, ly, default=0.5)
    a_wpct = _scalar_v2(coa, "team", "year", "career_win_pct", away_team, ly, default=0.5)
    f["home_new_coach"]     = int(h_new or 0)
    f["away_new_coach"]     = int(a_new or 0)
    f["coach_win_pct_diff"] = h_wpct - a_wpct

    h_elo = _scalar_v2(elo, "team", "year", "elo", home_team, ly, default=0.0)
    a_elo = _scalar_v2(elo, "team", "year", "elo", away_team, ly, default=0.0)
    f["elo_diff"] = h_elo - a_elo

    # Line Play features (using neutral defaults from training data)
    h_ly = _scalar_v2(line, "team", "season", "offense_lineYards", home_team, ly, default=None)
    a_ly = _scalar_v2(line, "team", "season", "offense_lineYards", away_team, ly, default=None)
    if h_ly is not None and a_ly is not None:
        f["offense_lineYards_diff"] = h_ly - a_ly
    elif h_ly is not None:
        f["offense_lineYards_diff"] = h_ly - 3.04
    elif a_ly is not None:
        f["offense_lineYards_diff"] = 3.04 - a_ly
    else:
        f["offense_lineYards_diff"] = 0.009

    h_sr = _scalar_v2(line, "team", "season", "defense_stuffRate", home_team, ly, default=None)
    a_sr = _scalar_v2(line, "team", "season", "defense_stuffRate", away_team, ly, default=None)
    if h_sr is not None and a_sr is not None:
        f["defense_stuffRate_diff"] = h_sr - a_sr
    elif h_sr is not None:
        f["defense_stuffRate_diff"] = h_sr - 0.179
    elif a_sr is not None:
        f["defense_stuffRate_diff"] = 0.179 - a_sr
    else:
        f["defense_stuffRate_diff"] = 0.0016

    f["neutral_site"] = 1 if neutral_site else 0
    f["home_field"]   = 0 if neutral_site else 1

    # Apply clips
    for col, (lo, hi) in _V2_FEATURE_CLIPS.items():
        if col in f:
            f[col] = max(lo, min(hi, f[col]))

    return f


def _load_v2_tables(season=None):
    """Load all reference tables once and return as a tuple."""
    return (
        _load_sp(),
        _load_recruiting(),
        _load_returning(),
        _load_coaches(),
        _load_elo(),
        _load_talent(),
        _load_portal_v2(),
        _load_line_play(season - 1) if season else None,
    )


def predict_win_probability_v2(
    home_team: str,
    away_team: str,
    season: int = 2025,
    neutral_site: bool = False,
):
    """Predict home-team win probability using the v2 17-feature model."""
    # 2026: use preseason composite fallbacks
    if season == 2026:
        return _predict_from_preseason_composite(home_team, away_team, "preseason_2026")

    _saved = os.path.join(os.path.dirname(__file__), "saved")
    model_path  = os.path.join(_saved, "win_prob_model_v2.pkl")
    cols_path   = os.path.join(_saved, "feature_cols_v2.pkl")
    scaler_path = os.path.join(_saved, "isotonic_calibrator_v2.joblib")

    if not os.path.exists(model_path):
        return "v2 model artifacts not found — run models/train_win_probability.py first"

    model        = joblib.load(model_path)
    feature_cols = joblib.load(cols_path)
    sp, rec, ret, coa, elo, talent, portal, line = _load_v2_tables(season)

    features = _build_features_v2(
        home_team, away_team, season,
        sp, rec, ret, coa, elo, talent, portal, line,
        neutral_site=neutral_site,
    )

    if features is None:
        return f"No SP+ data found for {home_team} or {away_team} in {season - 1}"

    X = pd.DataFrame([features])[feature_cols]
    
    # Raw lgbm prob
    raw_win_prob = round(float(model.predict_proba(X)[0][1]), 4)

    # Full calibrated model (CalibratedClassifierCV) includes isotonic step
    if os.path.exists(scaler_path):
        calibrated_model = joblib.load(scaler_path)
        win_prob = round(float(calibrated_model.predict_proba(X)[0][1]), 4)
    else:
        win_prob = raw_win_prob

    return {"win_prob": win_prob, "raw_win_prob": raw_win_prob}


def predict_win_probability_batch_v2(games: list, season: int) -> list:
    """Run v2 win probability prediction for multiple games in one vectorized call."""
    import logging
    logger = logging.getLogger(__name__)

    if not games:
        return []

    # 2026: use preseason composite ratings (vectorized)
    if season == 2026:
        comp_df = query_db("SELECT team, composite_100 FROM preseason_2026")
        scores = dict(zip(comp_df["team"], comp_df["composite_100"]))
        results = []
        for game in games:
            h = scores.get(game["home_team"])
            a = scores.get(game["away_team"])
            if h is None or a is None:
                continue
            diff = (h + _COMPOSITE_HOME_FIELD) - a
            prob = round(float(1.0 / (1.0 + np.exp(-_COMPOSITE_K * diff))), 4)
            results.append({
                **game,
                "home_win_prob":     prob,
                "away_win_prob":     round(1.0 - prob, 4),
                "raw_home_win_prob": prob,
            })
        return results

    _saved = os.path.join(os.path.dirname(__file__), "saved")
    model_path  = os.path.join(_saved, "win_prob_model_v2.pkl")
    cols_path   = os.path.join(_saved, "feature_cols_v2.pkl")
    scaler_path = os.path.join(_saved, "isotonic_calibrator_v2.joblib")

    if not os.path.exists(model_path):
        logger.error("v2 model artifacts not found — run models/train_win_probability.py first")
        return []

    lgbm_model   = joblib.load(model_path)
    feature_cols = joblib.load(cols_path)
    sp, rec, ret, coa, elo, talent, portal, line = _load_v2_tables(season)

    feature_rows = []
    valid_games  = []

    for game in games:
        features = _build_features_v2(
            game["home_team"], game["away_team"], season,
            sp, rec, ret, coa, elo, talent, portal, line,
            neutral_site=game.get("neutral_site", False),
        )
        if features is None:
            continue
        feature_rows.append(features)
        valid_games.append(game)

    if not feature_rows:
        return []

    X = pd.DataFrame(feature_rows)[feature_cols]
    raw_probs = lgbm_model.predict_proba(X)[:, 1]

    if os.path.exists(scaler_path):
        calibrated_model = joblib.load(scaler_path)
        cal_probs = calibrated_model.predict_proba(X)[:, 1]
    else:
        cal_probs = raw_probs

    results = []
    for game, raw_prob, cal_prob in zip(valid_games, raw_probs, cal_probs):
        home_win_prob = round(float(cal_prob), 4)
        results.append({
            **game,
            "home_win_prob":     home_win_prob,
            "away_win_prob":     round(1.0 - home_win_prob, 4),
            "raw_home_win_prob": round(float(raw_prob), 4),
        })

    return results
