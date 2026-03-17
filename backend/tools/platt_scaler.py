"""Platt scaling calibration for the LightGBM win probability model.

Backend copy — kept in sync with models/platt_scaler.py at the repo root.
Exposes calibrate_probability() for use by the backend inference path.
"""

import os
import numpy as np
import joblib

# Resolve the saved directory relative to this file:
# backend/tools/platt_scaler.py → backend/models/saved/
_SAVED_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "saved")
_SCALER_PATH = os.path.normpath(os.path.join(_SAVED_DIR, "platt_scaler.joblib"))


def calibrate_probability(raw_prob: float) -> float:
    """Apply the trained Platt scaler to a raw LightGBM probability.

    Loads the fitted CalibratedClassifierCV from disk and transforms a single
    raw probability value into a calibrated probability.  Falls back to the
    raw value if the scaler artifact does not exist (e.g. first deploy before
    training).

    Args:
        raw_prob: Raw win probability from the LightGBM model (0.0–1.0).

    Returns:
        Calibrated probability as a float rounded to 4 decimal places.
    """
    if not os.path.exists(_SCALER_PATH):
        return round(float(raw_prob), 4)

    calibrated = joblib.load(_SCALER_PATH)

    # Binary classification with cv='prefit': sklearn emits a single
    # _SigmoidCalibration at index 0 that maps raw P → calibrated P(class=1).
    calibrator = calibrated.calibrated_classifiers_[0].calibrators[0]
    cal_prob = calibrator.predict(np.array([raw_prob]))
    return round(float(cal_prob[0]), 4)
