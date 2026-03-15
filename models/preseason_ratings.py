"""
Composite preseason team strength rating.

Components and weights:
  SP+ final rating                   25%
  3-year recruiting avg              20%
  Returning production % PPA         20%  (conference-strength adjusted)
  Portal net stars                   20%
  Coach effectiveness score          15%

Coach effectiveness has three sub-components (all z-scored internally):
  Results alpha    40% — actual wins minus SP+-predicted wins per season,
                         averaged over seasons at current school (min 2).
  Portal ROI       40% — sp_rating / (normalized_recruiting_rank + 0.1).
                         High SP+ relative to recruiting prestige = good.
  YoY SP+ delta    20% — average annual SP+ change under current coach.

Each top-level component is z-scored across FBS teams before weighting.
Final composite is scaled 0-100.

NOTE: The 2024 backtest uses end-of-season SP+ ratings (the only form stored
in the DB), which introduces mild leakage. Treat the backtest as a structural
sanity check rather than a true out-of-sample test.
"""

import numpy as np
import pandas as pd
from db.database import query_db

WEIGHTS = {
    "sp":       0.25,
    "rec":      0.20,
    "ret":      0.20,
    "portal":   0.20,
    "coaching": 0.15,
}

HOME_FIELD_BOOST = 2.0   # composite points added to home team score

# ---------------------------------------------------------------------------
# Component builders
# ---------------------------------------------------------------------------

def build_sp(year: int) -> pd.DataFrame:
    """SP+ overall rating for each team."""
    return query_db(
        f"SELECT team, rating AS sp_rating FROM sp_ratings WHERE year = {year}"
    )


def build_recruiting(year: int) -> pd.DataFrame:
    """3-year rolling average of recruiting points (higher = better class)."""
    df = query_db(
        f"SELECT team, AVG(points) AS rec_3yr_avg "
        f"FROM recruiting_rankings "
        f"WHERE year BETWEEN {year - 2} AND {year} "
        f"GROUP BY team"
    )
    return df


CONF_MULTIPLIER = {
    # Power 4
    "SEC": 1.0, "Big Ten": 1.0, "Big 12": 1.0, "ACC": 1.0,
    # Independents
    "FBS Independents": 0.90,
    # Group of 5
    "American Athletic": 0.85, "Mountain West": 0.85,
    "Mid-American": 0.85, "Sun Belt": 0.85, "Conference USA": 0.85,
    # Pac-12 (2024 transition year — treat as P4)
    "Pac-12": 1.0,
}

def build_returning(year: int) -> pd.DataFrame:
    """
    Returning production as % of prior-year PPA (percentPPA), scaled by a
    conference-strength multiplier so G5 volume doesn't inflate the signal.
    """
    df = query_db(
        f'SELECT team, conference, "percentPPA" AS ret_ppa '
        f"FROM returning_production WHERE season = {year}"
    )
    df["conf_mult"] = df["conference"].map(CONF_MULTIPLIER).fillna(0.85)
    df["ret_ppa"]   = df["ret_ppa"] * df["conf_mult"]
    return df[["team", "ret_ppa"]]


def build_portal(year: int) -> pd.DataFrame:
    """
    Net portal score from portal_net_ratings table (built by stats_fetcher).
    FBS-only filter and eligibility weighting are applied at ingestion time.
    """
    df = query_db(
        f"SELECT team, net_portal_score AS portal_net "
        f"FROM portal_net_ratings WHERE season = {year}"
    )
    if df.empty:
        print(f"  Warning: no portal_net_ratings rows for {year}, skipping component.")
    return df


def build_coach_effectiveness(year: int) -> pd.DataFrame:
    """
    Three-component coach effectiveness score for each FBS team in `year`.

    Results alpha (40%)
      actual_wins - (6 + sp_rating/10) averaged over all seasons at current
      school with games played. Returns 0.0 when fewer than 2 seasons of data.

    Portal ROI (40%)
      sp_rating / (normalized_recruiting_rank + 0.1)
      Rank #1 → norm=1.0, rank #N → norm=0.0. Rewards coaches who outperform
      their recruiting prestige through development and portal efficiency.

    YoY SP+ improvement (20%)
      Mean annual SP+ change under this coach at this school. Positive = building.

    Sub-components are z-scored, then combined 40/40/20, then scaled 0-100.
    """
    # Load all raw data upfront
    coaches_all = query_db(
        'SELECT school, year, "firstName", "lastName", wins, games FROM coaches'
    )
    sp_all = query_db(
        "SELECT year, team AS school, rating AS sp_rating FROM sp_ratings"
    )
    rec_yr = query_db(
        f"SELECT team AS school, rank FROM recruiting_rankings WHERE year = {year}"
    )

    # Only use seasons with actual games for historical stats
    coaches_hist = coaches_all[coaches_all["games"] > 0].copy()
    coaches_hist = coaches_hist.sort_values(["school", "firstName", "lastName", "year"])

    # Join SP+ to historical records
    coaches_hist = coaches_hist.merge(sp_all, on=["school", "year"], how="left")
    coaches_hist["sp_rating"] = coaches_hist["sp_rating"].fillna(0.0)

    # Results alpha per season
    coaches_hist["predicted_wins"] = 6 + coaches_hist["sp_rating"] / 10
    coaches_hist["alpha"]          = coaches_hist["wins"] - coaches_hist["predicted_wins"]

    # YoY SP+ change (NaN for a coach's first season — mean() ignores it)
    coaches_hist["sp_lag"]    = coaches_hist.groupby(
        ["school", "firstName", "lastName"])["sp_rating"].shift(1)
    coaches_hist["sp_change"] = coaches_hist["sp_rating"] - coaches_hist["sp_lag"]

    # Aggregate per coach-school
    agg = (
        coaches_hist
        .groupby(["school", "firstName", "lastName"])
        .agg(n_seasons=("year", "count"),
             alpha_mean=("alpha", "mean"),
             yoy_mean=("sp_change", "mean"))
        .reset_index()
    )
    agg["results_alpha"]  = np.where(agg["n_seasons"] >= 2, agg["alpha_mean"], 0.0)
    agg["yoy_improvement"] = agg["yoy_mean"].fillna(0.0)

    # Portal ROI using this year's SP+ and recruiting rank
    sp_now  = sp_all[sp_all["year"] == year][["school", "sp_rating"]]
    n_teams = len(rec_yr)
    rec_yr  = rec_yr.copy()
    rec_yr["norm_rank"] = (n_teams - rec_yr["rank"]) / max(n_teams - 1, 1)
    roi_df  = sp_now.merge(rec_yr, on="school", how="left")
    roi_df["norm_rank"]  = roi_df["norm_rank"].fillna(0.5)
    roi_df["portal_roi"] = roi_df["sp_rating"] / (roi_df["norm_rank"] + 0.1)

    # Current-year coach roster (drop duplicates — keep most games played)
    coaches_now = (
        coaches_all[coaches_all["year"] == year]
        .sort_values("games", ascending=False)
        .drop_duplicates(subset="school")
        .copy()
    )

    # Merge all components
    coaches_now = coaches_now.merge(
        agg[["school", "firstName", "lastName", "n_seasons",
             "results_alpha", "yoy_improvement"]],
        on=["school", "firstName", "lastName"], how="left"
    )
    coaches_now = coaches_now.merge(roi_df[["school", "portal_roi"]], on="school", how="left")

    coaches_now["results_alpha"]   = coaches_now["results_alpha"].fillna(0.0)
    coaches_now["yoy_improvement"] = coaches_now["yoy_improvement"].fillna(0.0)
    coaches_now["n_seasons"]       = coaches_now["n_seasons"].fillna(1).astype(int)
    coaches_now["portal_roi"]      = coaches_now["portal_roi"].fillna(
        coaches_now["portal_roi"].median()
    )

    # Z-score sub-components and combine
    coaches_now["alpha_z"] = _zscore(coaches_now["results_alpha"])
    coaches_now["roi_z"]   = _zscore(coaches_now["portal_roi"])
    coaches_now["yoy_z"]   = _zscore(coaches_now["yoy_improvement"])
    coaches_now["eff_raw"] = (
        0.40 * coaches_now["alpha_z"] +
        0.40 * coaches_now["roi_z"]   +
        0.20 * coaches_now["yoy_z"]
    )

    lo, hi = coaches_now["eff_raw"].min(), coaches_now["eff_raw"].max()
    coaches_now["coach_effectiveness_score"] = 100 * (coaches_now["eff_raw"] - lo) / (hi - lo)
    coaches_now["coach"] = coaches_now["firstName"] + " " + coaches_now["lastName"]

    return (
        coaches_now[["school", "coach", "n_seasons",
                     "results_alpha", "portal_roi", "yoy_improvement",
                     "coach_effectiveness_score"]]
        .rename(columns={"school": "team"})
    )


# ---------------------------------------------------------------------------
# Composite builder
# ---------------------------------------------------------------------------

def _zscore(series: pd.Series) -> pd.Series:
    mu, sigma = series.mean(), series.std()
    return (series - mu) / sigma if sigma > 0 else pd.Series(0.0, index=series.index)


def save_composite(df: pd.DataFrame, table_name: str):
    from db.database import engine
    df.to_sql(table_name, con=engine, if_exists="replace", index=False)
    print(f"Saved {len(df)} rows to '{table_name}'")


def build_composite(year: int = 2024, data_years: dict = None, verbose: bool = True) -> pd.DataFrame:
    dy = {"sp": year, "rec": year, "ret": year, "portal": year, "coaching": year}
    if data_years:
        dy.update(data_years)

    if verbose:
        print(f"Building composite rating (SP+={dy['sp']}, rec={dy['rec']}, "
              f"ret={dy['ret']}, portal={dy['portal']}, coaching={dy['coaching']})...")

    sp       = build_sp(dy["sp"])
    rec      = build_recruiting(dy["rec"])
    ret      = build_returning(dy["ret"])
    portal   = build_portal(dy["portal"])
    coaching = build_coach_effectiveness(dy["coaching"])

    # Merge all components on team; SP+ provides the FBS team universe
    df = sp.copy()
    df = df.merge(rec,      on="team", how="left")
    df = df.merge(ret,      on="team", how="left")
    df = df.merge(portal,   on="team", how="left")
    df = df.merge(coaching, on="team", how="left")

    # Z-score each component (fill missing with 0 = FBS average)
    df["sp_z"]       = _zscore(df["sp_rating"].fillna(0))
    df["rec_z"]      = _zscore(df["rec_3yr_avg"].fillna(df["rec_3yr_avg"].median()))
    df["ret_z"]      = _zscore(df["ret_ppa"].fillna(0))
    df["portal_z"]   = _zscore(df["portal_net"].fillna(0))
    df["coaching_z"] = _zscore(df["coach_effectiveness_score"].fillna(df["coach_effectiveness_score"].median()))

    df["composite"] = (
        WEIGHTS["sp"]       * df["sp_z"] +
        WEIGHTS["rec"]      * df["rec_z"] +
        WEIGHTS["ret"]      * df["ret_z"] +
        WEIGHTS["portal"]   * df["portal_z"] +
        WEIGHTS["coaching"] * df["coaching_z"]
    )

    # Scale 0-100
    lo, hi = df["composite"].min(), df["composite"].max()
    df["composite_100"] = 100 * (df["composite"] - lo) / (hi - lo)

    return df.sort_values("composite_100", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

def backtest(year: int, composite_df: pd.DataFrame) -> float:
    games = query_db(f"""
        SELECT "homeTeam", "awayTeam", "homePoints", "awayPoints"
        FROM games
        WHERE season = {year}
          AND "homePoints" IS NOT NULL AND "awayPoints" IS NOT NULL
          AND "homeClassification" = 'fbs' AND "awayClassification" = 'fbs'
    """)

    scores = dict(zip(composite_df["team"], composite_df["composite_100"]))

    correct = total = home_wins = 0
    for _, game in games.iterrows():
        h = scores.get(game["homeTeam"])
        a = scores.get(game["awayTeam"])
        if h is None or a is None:
            continue
        predicted_home = (h + HOME_FIELD_BOOST) > a
        actual_home    = game["homePoints"] > game["awayPoints"]
        if actual_home:
            home_wins += 1
        if predicted_home == actual_home:
            correct += 1
        total += 1

    acc      = correct / total
    baseline = home_wins / total   # "always pick home team" baseline
    print(f"\nBacktest {year}: {correct}/{total} correct  —  {acc:.2%} accuracy")
    print(f"Baseline (always home): {baseline:.2%}")
    print(f"Lift over baseline: +{(acc - baseline)*100:.1f} pp")
    return acc


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _display_component(row):
    return (
        f"SP+={row['sp_rating']:>5.1f}  "
        f"Rec={row['rec_3yr_avg']:>6.1f}  "
        f"RetPct={row['ret_ppa']:>5.3f}  "
        f"Portal={row['portal_net']:>+5.1f}  "
        f"CoachEff={row['coach_effectiveness_score']:>5.1f}"
    )


def _print_rankings(label: str, df: pd.DataFrame, n_top: int = 25, n_bottom: int = 10):
    disp_cols = ["sp_rating", "rec_3yr_avg", "ret_ppa", "portal_net", "coach_effectiveness_score"]
    for col in disp_cols:
        df[col] = df[col].fillna(0)

    print(f"\n{'='*80}")
    print(f"  TOP {n_top} — {label}")
    print(f"{'='*80}")
    print(f"  {'Rank':<5} {'Team':<25} {'Score':>6}  Components")
    print(f"  {'-'*74}")
    for i, row in df.head(n_top).iterrows():
        print(f"  {i+1:<5} {row['team']:<25} {row['composite_100']:>5.1f}  {_display_component(row)}")

    print(f"\n{'='*80}")
    print(f"  BOTTOM 10 — {label}")
    print(f"{'='*80}")
    print(f"  {'Rank':<5} {'Team':<25} {'Score':>6}  Components")
    print(f"  {'-'*74}")
    for i, row in df.tail(n_bottom).iterrows():
        print(f"  {i+1:<5} {row['team']:<25} {row['composite_100']:>5.1f}  {_display_component(row)}")


def _print_coach_leaderboard(coaching_df: pd.DataFrame, year: int):
    df = coaching_df.sort_values("coach_effectiveness_score", ascending=False).reset_index(drop=True)
    print(f"\n{'='*80}")
    print(f"  TOP 10 COACHES — {year} Effectiveness Score")
    print(f"{'='*80}")
    print(f"  {'#':<4} {'Coach':<22} {'Team':<22} {'Eff':>5}  "
          f"{'Alpha':>6}  {'PortROI':>7}  {'YoY':>6}  {'Yrs':>3}")
    print(f"  {'-'*74}")
    for i, row in df.head(10).iterrows():
        print(f"  {i+1:<4} {row['coach']:<22} {row['team']:<22} {row['coach_effectiveness_score']:>5.1f}  "
              f"{row['results_alpha']:>+6.2f}  {row['portal_roi']:>7.1f}  "
              f"{row['yoy_improvement']:>+6.2f}  {int(row['n_seasons']):>3}")

    print(f"\n{'='*80}")
    print(f"  BOTTOM 10 COACHES — {year} Effectiveness Score")
    print(f"{'='*80}")
    print(f"  {'#':<4} {'Coach':<22} {'Team':<22} {'Eff':>5}  "
          f"{'Alpha':>6}  {'PortROI':>7}  {'YoY':>6}  {'Yrs':>3}")
    print(f"  {'-'*74}")
    for i, row in df.tail(10).sort_values("coach_effectiveness_score").iterrows():
        print(f"  {i+1:<4} {row['coach']:<22} {row['team']:<22} {row['coach_effectiveness_score']:>5.1f}  "
              f"{row['results_alpha']:>+6.2f}  {row['portal_roi']:>7.1f}  "
              f"{row['yoy_improvement']:>+6.2f}  {int(row['n_seasons']):>3}")

    # Indiana / Cignetti callout
    cignetti = df[df["coach"].str.contains("Cignetti", case=False)]
    if not cignetti.empty:
        r = cignetti.iloc[0]
        rank = df.index[df["coach"].str.contains("Cignetti", case=False)].tolist()[0] + 1
        note = "(results_alpha=0.0: only 1 season with data — minimum 2 required)" \
               if r["n_seasons"] < 2 else ""
        print(f"\n  --- Indiana / Curt Cignetti (rank #{rank}) ---")
        print(f"  Eff={r['coach_effectiveness_score']:.1f}  Alpha={r['results_alpha']:+.2f}  "
              f"PortROI={r['portal_roi']:.1f}  YoY={r['yoy_improvement']:+.2f}  "
              f"Seasons={int(r['n_seasons'])}  {note}")


if __name__ == "__main__":
    YEAR = 2024

    composite = build_composite(YEAR)
    _print_rankings(f"{YEAR} Composite Preseason Rating", composite)
    backtest(YEAR, composite)

    # Coach leaderboard for 2024
    coaches_2024 = build_coach_effectiveness(YEAR)
    _print_coach_leaderboard(coaches_2024, YEAR)

    # ------------------------------------------------------------------
    # 2026 preseason — per-component years since they differ
    #   SP+ / recruiting / returning production : 2025 (most recent final)
    #   Portal                                  : 2026 class (available)
    #   Coaching                                : 2025 (2026 data not yet
    #                                             in CFBD API)
    # ------------------------------------------------------------------
    composite_2026 = build_composite(
        year=2025,
        data_years={"portal": 2026, "coaching": 2025},
    )
    save_composite(composite_2026, "preseason_2026")
    _print_rankings("2026 Preseason Composite Rating", composite_2026)

    # Coach leaderboard for 2025 (used in 2026 preseason)
    coaches_2025 = build_coach_effectiveness(2025)
    _print_coach_leaderboard(coaches_2025, 2025)
