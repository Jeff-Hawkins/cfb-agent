# Predictions Skill — cfb-agent

## Model
LightGBM V2 (production). V3 retrain in progress (Phase 8B).
Artifacts: `models/saved/win_prob_model_v2.pkl`, `models/saved/platt_scaler_v2.joblib`, `models/saved/feature_cols_v2.pkl`
Load via `models/win_probability.py` — never load artifacts directly.

## Flag Thresholds (constants.py — single source of truth)
```python
MAX_SPREAD = 17          # abs(spread) <= 17
MIN_WIN_PROB = 0.65      # win_prob >= 0.65
MIN_SPREAD_DIFF = 5.0    # abs(spread_diff) >= 5.0
```
Always import from `backend/constants.py`. Never hardcode thresholds.

## Spread Diff Formula
```python
# home pick
model_implied = -1 * (win_prob - 0.5) * 28
spread_diff = actual_spread - model_implied

# away pick
model_implied = (win_prob - 0.5) * 28
spread_diff = actual_spread - model_implied
```

## Neutral Site Defaults
neutral_site_flag = 0.009
neutral_site_std = 0.0016

## Fallback Values
home_field_advantage fallback: 3.04
spread fallback: 0.179

## Feature List (V2 — 17 features)
offense_lineYards_diff, defense_stuffRate_diff, sp_plus_diff,
recruiting_3yr_avg_diff, returning_production_diff, portal_net_diff,
coach_effectiveness_diff, recency_weight, home_field_advantage,
elo_diff, talent_diff, neutral_site, conference_multiplier,
offense_ppa_diff (if available), defense_ppa_diff (if available),
success_rate_diff (if available), defense_havoc_diff (if available)

## Batch Prediction
Always use `predict_win_probability_batch()` for multiple games.
Never call single-game prediction in a loop — causes Railway timeout.

## Win Probability Display
Round to 2 decimal places for display.
Spread values: always `toFixed(1)` on frontend.
