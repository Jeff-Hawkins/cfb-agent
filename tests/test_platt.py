"""Tests for the Platt scaler calibration module (models/platt_scaler.py)."""

import os
import sys
import unittest

# Ensure repo root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestCalibrateInRange(unittest.TestCase):
    def test_calibrate_probability_in_range(self):
        """calibrate_probability must return a float between 0 and 1."""
        from models.platt_scaler import calibrate_probability
        result = calibrate_probability(0.65)
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)


class TestCalibratedDiffersFromRaw(unittest.TestCase):
    def test_calibrated_differs_from_raw(self):
        """Calibrated probability for input 0.72 must differ from the raw value."""
        from models.platt_scaler import calibrate_probability
        raw = 0.72
        calibrated = calibrate_probability(raw)
        self.assertNotEqual(calibrated, raw)


class TestScalerArtifactExists(unittest.TestCase):
    def test_scaler_artifact_exists(self):
        """models/saved/platt_scaler.joblib must exist on disk."""
        root = os.path.join(os.path.dirname(__file__), "..")
        path = os.path.normpath(os.path.join(root, "models", "saved", "platt_scaler.joblib"))
        self.assertTrue(os.path.exists(path), f"Scaler artifact not found at {path}")


if __name__ == "__main__":
    unittest.main()
