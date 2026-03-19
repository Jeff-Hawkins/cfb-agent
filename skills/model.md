# Model Skill — cfb-agent

## Production Model
V2 (default). V3 available via MODEL_VERSION=v3 env var on Railway.

## V2 Artifacts
models/saved/win_prob_model_v2.pkl
models/saved/platt_scaler_v2.joblib
models/saved/feature_cols_v2.pkl
Accuracy: 64.59% | Brier: 0.2152

## V3 Artifacts
models/saved/lgbm_v3.pkl
models/saved/calibrator_v3.pkl
models/saved/feature_list_v3.json
Accuracy: 65.95% | Brier: 0.2144

## Loading Pattern
Never load artifacts directly. Always use:
  from backend.models.win_probability import predict_win_probability_batch

## Switching to V3 on Railway
1. Review training report
2. Set MODEL_VERSION=v3 in Railway dashboard environment variables
3. Railway auto-redeploys
4. Monitor /games endpoint for 24 hours before confirming

## Neutral Defaults (inference time)
neutral_site_flag = 0.009
neutral_site_std = 0.0016
home_field_advantage fallback = 3.04

## Flag Thresholds (constants.py)
abs(spread) <= 17
win_prob >= 0.65
abs(spread_diff) >= 5.0
