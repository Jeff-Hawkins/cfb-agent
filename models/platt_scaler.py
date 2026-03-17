"""Platt scaling calibration for the LightGBM win probability model.

Trains a sigmoid (Platt) calibration layer on top of the raw LightGBM
probabilities, then exposes a simple calibrate_probability() function
for use in inference.
"""

import os
import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV

# Path to the models/saved directory, relative to this file
_SAVED_DIR = os.path.join(os.path.dirname(__file__), "saved")
_SCALER_PATH = os.path.join(_SAVED_DIR, "platt_scaler.joblib")


def train_platt_scaler() -> None:
    """Train a Platt scaler on LightGBM outputs and save it to disk.

    Loads the existing LightGBM model from models/saved/win_prob_model.pkl,
    builds training data via build_training_data(), then fits a
    CalibratedClassifierCV with method='sigmoid' (Platt scaling) on the full
    training set. The fitted calibrated classifier is saved to
    models/saved/platt_scaler.joblib.

    This function is safe to call from the command line:
        python -c "from models.platt_scaler import train_platt_scaler; train_platt_scaler()"
    """
    from models.win_probability import build_training_data

    os.makedirs(_SAVED_DIR, exist_ok=True)

    model_path = os.path.join(_SAVED_DIR, "win_prob_model.pkl")
    feature_cols_path = os.path.join(_SAVED_DIR, "feature_cols.pkl")

    print("Loading LightGBM model...")
    base_model = joblib.load(model_path)
    feature_cols = joblib.load(feature_cols_path)

    print("Building training data...")
    df, _ = build_training_data()

    feature_cols_present = [c for c in feature_cols if c in df.columns]
    X = df[feature_cols_present]
    y = df["home_win"]

    print(f"Training Platt scaler on {len(X)} samples...")
    # cv='prefit' tells CalibratedClassifierCV that the base estimator is
    # already trained — it will fit the sigmoid layer on the provided data.
    calibrated = CalibratedClassifierCV(estimator=base_model, method="sigmoid", cv="prefit")
    calibrated.fit(X, y)

    joblib.dump(calibrated, _SCALER_PATH)
    print(f"Platt scaler saved to {_SCALER_PATH}")


def calibrate_probability(raw_prob: float) -> float:
    """Apply the trained Platt scaler to a raw LightGBM probability.

    Loads the fitted CalibratedClassifierCV from disk and transforms a single
    raw probability value into a calibrated probability. The scaler is loaded
    fresh on every call so that model updates on disk are picked up
    automatically.

    Args:
        raw_prob: Raw win probability from the LightGBM model (0.0–1.0).

    Returns:
        Calibrated probability as a float rounded to 4 decimal places.
        Falls back to raw_prob if the scaler artifact does not exist.
    """
    if not os.path.exists(_SCALER_PATH):
        # Graceful fallback: if scaler hasn't been trained yet, return raw
        return round(float(raw_prob), 4)

    calibrated = joblib.load(_SCALER_PATH)

    # CalibratedClassifierCV.predict_proba requires the full feature matrix
    # (same shape as the base LightGBM model), so we call the underlying
    # sigmoid calibrator directly with just the scalar raw probability.
    # Binary classification with cv='prefit': sklearn emits a single
    # _SigmoidCalibration at index 0 that maps raw P → calibrated P(class=1).
    calibrator = calibrated.calibrated_classifiers_[0].calibrators[0]
    cal_prob = calibrator.predict(np.array([raw_prob]))
    return round(float(cal_prob[0]), 4)


if __name__ == "__main__":
    train_platt_scaler()
