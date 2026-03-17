"""Router for /bayesian endpoints.

Provides:
  POST /bayesian/update  — admin-protected, triggers weekly Bayesian model update
  GET  /bayesian/performance — public, returns per-week performance history for a season
"""

import logging
from fastapi import APIRouter, BackgroundTasks, Depends, Query

from routers.picks import _require_admin

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/update")
def bayesian_update(
    season: int = Query(..., description="Season year"),
    week: int = Query(..., description="Most recently completed week"),
    background_tasks: BackgroundTasks = None,
    _: None = Depends(_require_admin),
):
    """Trigger the weekly Bayesian model update as a background task.

    Enqueues run_weekly_bayesian_update(season, week) so the response
    returns immediately without waiting for the refit to complete.

    Args:
        season: Season year.
        week: Most recently completed CFB week.

    Returns:
        Immediate acknowledgement dict.
    """
    from tools.bayesian_updater import run_weekly_bayesian_update

    if background_tasks is not None:
        background_tasks.add_task(run_weekly_bayesian_update, season, week)

    return {"status": "update started", "season": season, "week": week}


@router.get("/performance")
def get_performance(
    season: int = Query(..., description="Season year"),
):
    """Return per-week model performance history for the season.

    Iterates weeks 1–15 and calls calculate_weekly_performance() for each
    week that has at least one pick with a resolved outcome. Weeks with no
    data are omitted from the response.

    Args:
        season: Season year.

    Returns:
        List of weekly performance dicts sorted by week ascending.
    """
    from tools.bayesian_updater import calculate_weekly_performance

    results = []
    for week in range(1, 16):
        try:
            perf = calculate_weekly_performance(season, week)
            if perf["picks"] > 0:
                results.append(perf)
        except Exception as exc:
            logger.warning("Could not fetch performance for season=%d week=%d: %s", season, week, exc)

    return results
