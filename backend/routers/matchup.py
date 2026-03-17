"""Router for the /matchup endpoint.

Returns win probability for a home vs. away matchup using the trained
LightGBM model from models/win_probability.py.
"""

from fastapi import APIRouter, HTTPException, Query
from models.win_probability import predict_win_probability

router = APIRouter()


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
        "model_version": "2.0.0",
    }
