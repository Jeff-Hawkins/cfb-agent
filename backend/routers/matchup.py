"""Router for the /matchup endpoint.

Returns win probability for a home vs. away matchup using the trained
LightGBM model from models/win_probability.py.
"""

import os
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.win_probability import (
    predict_win_probability,
    predict_win_probability_v2,
    MODEL_VERSION,
    MODEL_VERSION_V2,
)

router = APIRouter()
_security = HTTPBearer()


def _require_admin(credentials: HTTPAuthorizationCredentials = Depends(_security)):
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected or credentials.credentials != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("")
def get_matchup(
    home: str = Query(..., description="Home team name"),
    away: str = Query(..., description="Away team name"),
    season: int = Query(2025, description="Season year"),
):
    """Return win probabilities for a given home/away matchup.

    Calls the trained win probability model. If either team is not found in
    the model's data, returns a 404 with the model's error message.
    """
    result = predict_win_probability(home, away, season)

    if isinstance(result, str):
        raise HTTPException(status_code=404, detail=result)

    # predict_win_probability returns a dict with win_prob and raw_win_prob
    # for non-error cases (season != 2026 or preseason fallback is a float)
    if isinstance(result, dict):
        home_win_prob = result["win_prob"]
        raw_win_prob = result["raw_win_prob"]
    else:
        home_win_prob = result
        raw_win_prob = result

    return {
        "home_team": home,
        "away_team": away,
        "season": season,
        "home_win_probability": home_win_prob,
        "away_win_probability": round(1.0 - home_win_prob, 4),
        "raw_home_win_probability": raw_win_prob,
        "model_version": MODEL_VERSION,
    }


@router.get("/compare")
def compare_models(
    home: str = Query(..., description="Home team name"),
    away: str = Query(..., description="Away team name"),
    season: int = Query(2025, description="Season year"),
    _: HTTPAuthorizationCredentials = Depends(_require_admin),
):
    """Return v1 and v2 win probability predictions side by side (admin only).

    Useful for validating the v2 retrain before swapping it into production.
    Returns predictions from both models and the delta between them.
    """
    v1 = predict_win_probability(home, away, season)
    v2 = predict_win_probability_v2(home, away, season)

    if isinstance(v1, str):
        raise HTTPException(status_code=404, detail=f"v1: {v1}")
    if isinstance(v2, str):
        raise HTTPException(status_code=404, detail=f"v2: {v2}")

    v1_prob = v1["win_prob"] if isinstance(v1, dict) else float(v1)
    v2_prob = v2["win_prob"]

    return {
        "home_team": home,
        "away_team": away,
        "season": season,
        "v1": {
            "win_prob":     v1_prob,
            "raw_win_prob": v1["raw_win_prob"] if isinstance(v1, dict) else v1_prob,
            "model_version": MODEL_VERSION,
        },
        "v2": {
            "win_prob":     v2_prob,
            "raw_win_prob": v2["raw_win_prob"],
            "model_version": MODEL_VERSION_V2,
        },
        "delta": round(abs(v1_prob - v2_prob), 4),
    }
