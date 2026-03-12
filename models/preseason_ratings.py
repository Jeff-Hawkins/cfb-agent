"""
Composite preseason team strength rating.

Components and weights:
  SP+ final rating                   30%
  3-year recruiting avg              20%
  Returning production % PPA         20%  (conference-strength adjusted)
  Portal net stars                   20%
  Coaching stability                 10%

Each component is z-scored across FBS teams before weighting so no single
range dominates the composite. Final score is scaled 0-100.

NOTE: The 2024 backtest uses end-of-season SP+ ratings (the only form stored
in the DB), which introduces mild leakage. Treat the backtest as a structural
sanity check rather than a true out-of-sample test.
"""

import numpy as np
import pandas as pd
from db.database import query_db

WEIGHTS = {
    "sp":       0.30,
    "rec":      0.20,
    "ret":      0.20,
    "portal":   0.20,
    "coaching": 0.10,
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
        f"SELECT team, conference, percentPPA AS ret_ppa "
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


def build_coaching(year: int) -> pd.DataFrame:
    """
    Coaching stability score = years_at_school * career_win_pct.
    A veteran coach with a winning record scores highest;
    a first-year coach or one with a losing record scores lowest.
    """
    coaches = query_db(
        "SELECT school, year, firstName, lastName, wins, losses, games FROM coaches"
    )
    coaches = coaches.sort_values(["firstName", "lastName", "year"])

    # Years at this school
    first_yr = (
        coaches.groupby(["school", "firstName", "lastName"])["year"]
        .min().reset_index().rename(columns={"year": "first_year"})
    )
    coaches = coaches.merge(first_yr, on=["school", "firstName", "lastName"])
    coaches["years_at_school"] = coaches["year"] - coaches["first_year"] + 1

    # Career win% (cumulative up to each season)
    coaches["career_wins"]  = coaches.groupby(["firstName", "lastName"])["wins"].cumsum()
    coaches["career_games"] = coaches.groupby(["firstName", "lastName"])["games"].cumsum()
    coaches["career_win_pct"] = (
        coaches["career_wins"] / coaches["career_games"].replace(0, np.nan)
    ).fillna(0.5)

    year_df = coaches[coaches["year"] == year].copy()
    year_df["coaching_score"] = year_df["years_at_school"] * year_df["career_win_pct"]

    # Keep the highest-scoring coach per school (handles mid-season HC changes)
    year_df = (
        year_df.sort_values("coaching_score", ascending=False)
        .drop_duplicates(subset="school")
    )

    return (
        year_df[["school", "coaching_score"]]
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
    coaching = build_coaching(dy["coaching"])

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
    df["coaching_z"] = _zscore(df["coaching_score"].fillna(df["coaching_score"].median()))

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
        SELECT homeTeam, awayTeam, homePoints, awayPoints
        FROM games
        WHERE season = {year}
          AND homePoints IS NOT NULL AND awayPoints IS NOT NULL
          AND homeClassification = 'fbs' AND awayClassification = 'fbs'
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
        f"CoachScore={row['coaching_score']:>5.2f}"
    )


if __name__ == "__main__":
    YEAR = 2024

    composite = build_composite(YEAR)

    # Fill display NaNs
    for col in ["sp_rating", "rec_3yr_avg", "ret_ppa", "portal_net", "coaching_score"]:  # noqa
        composite[col] = composite[col].fillna(0)

    print(f"\n{'='*75}")
    print(f"  TOP 25 — {YEAR} Composite Preseason Rating")
    print(f"{'='*75}")
    print(f"  {'Rank':<5} {'Team':<25} {'Score':>6}  Components")
    print(f"  {'-'*70}")
    for i, row in composite.head(25).iterrows():
        print(f"  {i+1:<5} {row['team']:<25} {row['composite_100']:>5.1f}  {_display_component(row)}")

    print(f"\n{'='*75}")
    print(f"  BOTTOM 10 — {YEAR} Composite Preseason Rating")
    print(f"{'='*75}")
    print(f"  {'Rank':<5} {'Team':<25} {'Score':>6}  Components")
    print(f"  {'-'*70}")
    for i, row in composite.tail(10).iterrows():
        print(f"  {i+1:<5} {row['team']:<25} {row['composite_100']:>5.1f}  {_display_component(row)}")

    backtest(YEAR, composite)

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

    for col in ["sp_rating", "rec_3yr_avg", "ret_ppa", "portal_net", "coaching_score"]:
        composite_2026[col] = composite_2026[col].fillna(0)

    print(f"\n{'='*75}")
    print(f"  TOP 25 — 2026 Preseason Composite Rating")
    print(f"{'='*75}")
    print(f"  {'Rank':<5} {'Team':<25} {'Score':>6}  Components")
    print(f"  {'-'*70}")
    for i, row in composite_2026.head(25).iterrows():
        print(f"  {i+1:<5} {row['team']:<25} {row['composite_100']:>5.1f}  {_display_component(row)}")

    print(f"\n{'='*75}")
    print(f"  BOTTOM 10 — 2026 Preseason Composite Rating")
    print(f"{'='*75}")
    print(f"  {'Rank':<5} {'Team':<25} {'Score':>6}  Components")
    print(f"  {'-'*70}")
    for i, row in composite_2026.tail(10).iterrows():
        print(f"  {i+1:<5} {row['team']:<25} {row['composite_100']:>5.1f}  {_display_component(row)}")
