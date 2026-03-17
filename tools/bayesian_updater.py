"""Bayesian in-season updating for the CFB Agent win probability model.

After each week's results, this module:
  1. Calculates model performance metrics for the week.
  2. Re-fits the Platt scaler using the full training set so calibration
     reflects any drift seen in live picks.
  3. Sends a summary email via SendGrid.

Root copy — kept in sync with backend/tools/bayesian_updater.py.
Path constants resolve correctly from either location via __file__.
"""

import os
import logging
import numpy as np
import joblib

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path resolution — works from both tools/ (root) and backend/tools/
# ---------------------------------------------------------------------------

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT  = os.path.normpath(os.path.join(_TOOLS_DIR, ".."))

_PRIMARY_SCALER   = os.path.join(_REPO_ROOT, "models", "saved", "platt_scaler.joblib")
_SECONDARY_SCALER = os.path.join(_REPO_ROOT, "backend", "models", "saved", "platt_scaler.joblib")
_MODEL_PATH        = os.path.join(_REPO_ROOT, "models", "saved", "win_prob_model.pkl")
_FEATURE_COLS_PATH = os.path.join(_REPO_ROOT, "models", "saved", "feature_cols.pkl")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _brier_score(y_true: list, y_prob: list) -> float:
    """Compute Brier score — mean squared error between probabilities and outcomes."""
    return sum((p - y) ** 2 for p, y in zip(y_prob, y_true)) / len(y_true)


def _load_calibrator(scaler_path: str):
    """Load the sigmoid calibrator from a saved CalibratedClassifierCV artifact."""
    if not os.path.exists(scaler_path):
        return None
    try:
        calibrated = joblib.load(scaler_path)
        return calibrated.calibrated_classifiers_[0].calibrators[0]
    except Exception as exc:
        logger.warning("Could not load calibrator from %s: %s", scaler_path, exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_weekly_performance(season: int, week: int) -> dict:
    """Calculate model performance metrics for a given season/week.

    Fetches all approved picks with resolved outcomes and computes win rate,
    average win probability on wins/losses, and Brier score.

    Args:
        season: Season year.
        week: CFB week number.

    Returns:
        Dict with keys: season, week, picks, wins, losses, win_rate,
        avg_win_prob_on_wins, avg_win_prob_on_losses, brier_score_week.
    """
    from db.database import query_db

    df = query_db(f"""
        SELECT win_probability, outcome
        FROM picks
        WHERE season = {season}
          AND week = {week}
          AND approved = true
          AND outcome IS NOT NULL
    """)

    empty = {
        "season": season, "week": week,
        "picks": 0, "wins": 0, "losses": 0,
        "win_rate": 0.0,
        "avg_win_prob_on_wins": 0.0,
        "avg_win_prob_on_losses": 0.0,
        "brier_score_week": 0.0,
    }

    if df.empty:
        return empty

    wins_mask   = df["outcome"] == "WIN"
    losses_mask = df["outcome"] == "LOSS"
    wins   = int(wins_mask.sum())
    losses = int(losses_mask.sum())
    total  = wins + losses

    if total == 0:
        return empty

    win_rate        = wins / total
    avg_wp_wins     = float(df.loc[wins_mask, "win_probability"].mean()) if wins > 0 else 0.0
    avg_wp_losses   = float(df.loc[losses_mask, "win_probability"].mean()) if losses > 0 else 0.0

    y_true = [1 if o == "WIN" else 0 for o in df["outcome"]]
    y_prob = df["win_probability"].tolist()
    brier  = _brier_score(y_true, y_prob)

    return {
        "season": season,
        "week": week,
        "picks": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 4),
        "avg_win_prob_on_wins": round(avg_wp_wins, 4),
        "avg_win_prob_on_losses": round(avg_wp_losses, 4),
        "brier_score_week": round(brier, 4),
    }


def update_platt_scaler(season: int, week: int) -> dict:
    """Re-fit the Platt scaler if at least 20 picks with outcomes exist.

    Loads all approved picks with resolved outcomes for the season to date,
    computes the old Brier score on those picks, then retrains the full
    CalibratedClassifierCV using the complete training dataset. The new
    scaler is saved and the new Brier score on picks is returned for
    comparison.

    Only updates if len(picks_with_outcomes) >= 20.

    Args:
        season: Season year (used to scope picks).
        week: Current week (informational — included in return dict).

    Returns:
        Dict with keys: picks_used, old_brier, new_brier, updated (bool).
    """
    from db.database import query_db
    from sklearn.calibration import CalibratedClassifierCV

    df = query_db(f"""
        SELECT win_probability, outcome
        FROM picks
        WHERE season = {season}
          AND approved = true
          AND outcome IS NOT NULL
    """)

    no_update = {"picks_used": len(df), "old_brier": None, "new_brier": None, "updated": False}

    if len(df) < 20:
        logger.info(
            "Bayesian update skipped — only %d picks with outcomes (need 20)", len(df)
        )
        return no_update

    y_true = [1 if o == "WIN" else 0 for o in df["outcome"]]
    y_prob = df["win_probability"].tolist()

    # Brier score under existing scaler
    calibrator = _load_calibrator(_PRIMARY_SCALER)
    if calibrator is not None:
        old_preds = [float(calibrator.predict(np.array([p]))[0]) for p in y_prob]
        old_brier = round(_brier_score(y_true, old_preds), 4)
    else:
        old_brier = round(_brier_score(y_true, y_prob), 4)

    # Re-fit scaler on full training data
    try:
        from models.win_probability import build_training_data

        base_model   = joblib.load(_MODEL_PATH)
        feature_cols = joblib.load(_FEATURE_COLS_PATH)
        train_df, _  = build_training_data()

        present = [c for c in feature_cols if c in train_df.columns]
        X = train_df[present]
        y = train_df["home_win"]

        calibrated = CalibratedClassifierCV(estimator=base_model, method="sigmoid", cv="prefit")
        calibrated.fit(X, y)

    except Exception as exc:
        logger.error("Platt scaler refit failed: %s", exc)
        return no_update

    # Brier score under new scaler
    new_cal   = calibrated.calibrated_classifiers_[0].calibrators[0]
    new_preds = [float(new_cal.predict(np.array([p]))[0]) for p in y_prob]
    new_brier = round(_brier_score(y_true, new_preds), 4)

    # Persist — primary path always; secondary path only if directory exists
    joblib.dump(calibrated, _PRIMARY_SCALER)
    secondary_dir = os.path.dirname(_SECONDARY_SCALER)
    if os.path.isdir(secondary_dir):
        try:
            joblib.dump(calibrated, _SECONDARY_SCALER)
        except Exception as exc:
            logger.warning("Could not save scaler to secondary path: %s", exc)

    logger.info(
        "Platt scaler updated — %d picks, old Brier=%.4f, new Brier=%.4f",
        len(df), old_brier, new_brier,
    )

    return {
        "picks_used": len(df),
        "old_brier": old_brier,
        "new_brier": new_brier,
        "updated": True,
    }


def send_bayesian_update_notification(update_result: dict) -> None:
    """Send a model update summary email via SendGrid.

    Args:
        update_result: Dict as returned by run_weekly_bayesian_update().

    The function silently logs errors and never raises so callers are not
    disrupted by email delivery failures.
    """
    api_key       = os.getenv("SENDGRID_API_KEY", "")
    notify_email  = os.getenv("NOTIFY_EMAIL", "")

    if not api_key or not notify_email:
        logger.warning(
            "SENDGRID_API_KEY or NOTIFY_EMAIL not set — skipping Bayesian update email"
        )
        return

    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail

        season = update_result.get("season", "?")
        week   = update_result.get("week", "?")
        pu     = update_result.get("picks_used", 0)
        ob     = update_result.get("old_brier")
        nb     = update_result.get("new_brier")
        did_update = update_result.get("updated", False)

        lines = [
            f"Season: {season}  |  Week: {week}",
            f"Picks with outcomes: {pu}",
            f"Old Brier score: {ob if ob is not None else 'n/a'}",
            f"New Brier score: {nb if nb is not None else 'n/a'}",
            f"Scaler updated: {'YES' if did_update else 'NO (< 20 picks or refit failed)'}",
        ]

        body = "CFB Agent — Weekly Bayesian Model Update\n\n" + "\n".join(lines)

        message = Mail(
            from_email=notify_email,
            to_emails=notify_email,
            subject=f"CFB Agent — Weekly Model Update (Week {week}, {season})",
            plain_text_content=body,
        )

        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        response = sg.send(message)
        logger.info(
            "Bayesian update email sent (status %s) for Week %s %s",
            response.status_code, week, season,
        )

    except Exception as exc:
        logger.error("Failed to send Bayesian update email: %s", exc)


def run_weekly_bayesian_update(season: int, week: int) -> dict:
    """Orchestrate the full weekly Bayesian update pipeline.

    Calls calculate_weekly_performance(), update_platt_scaler(), and
    send_bayesian_update_notification() in sequence. Wraps everything in
    try/except so the cron job never crashes on partial failures.

    Args:
        season: Season year.
        week: CFB week number (most recently completed week).

    Returns:
        Combined result dict with keys from both calculate_weekly_performance
        and update_platt_scaler, plus season and week.
    """
    result = {"season": season, "week": week}

    try:
        perf = calculate_weekly_performance(season, week)
        result.update(perf)
    except Exception as exc:
        logger.error("calculate_weekly_performance failed (season=%d week=%d): %s", season, week, exc)

    try:
        scaler_result = update_platt_scaler(season, week)
        result.update(scaler_result)
    except Exception as exc:
        logger.error("update_platt_scaler failed (season=%d week=%d): %s", season, week, exc)
        result.update({"picks_used": 0, "old_brier": None, "new_brier": None, "updated": False})

    try:
        send_bayesian_update_notification(result)
    except Exception as exc:
        logger.error("send_bayesian_update_notification failed: %s", exc)

    return result
