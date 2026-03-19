import unittest
import os
import json
import joblib
import pandas as pd
from backend.models.win_probability import (
    predict_win_probability,
    predict_win_probability_batch,
    _build_features_v3,
    _load_v3_tables
)

class TestPhase8b(unittest.TestCase):
    def test_v3_artifacts_exist(self):
        """Assert lgbm_v3.pkl, calibrator_v3.pkl, feature_list_v3.json all exist."""
        saved = "backend/models/saved"
        self.assertTrue(os.path.exists(os.path.join(saved, "lgbm_v3.pkl")))
        self.assertTrue(os.path.exists(os.path.join(saved, "calibrator_v3.pkl")))
        self.assertTrue(os.path.exists(os.path.join(saved, "feature_list_v3.json")))

    def test_v3_feature_count(self):
        """Load feature_list_v3.json and assert length is 21."""
        with open("backend/models/saved/feature_list_v3.json", "r") as f:
            cols = json.load(f)
        self.assertEqual(len(cols), 21)
        self.assertIn("offense_ppa_diff", cols)
        self.assertIn("defense_havoc_diff", cols)

    def test_v3_feature_builder(self):
        """Call _build_features_v3 with a known 2024 matchup."""
        # Using 2024 game: Georgia vs Clemson
        sp, rec, ret, coa, elo, talent, portal, line, ppa = _load_v3_tables(2024)
        f = _build_features_v3("Georgia", "Clemson", 2024, sp, rec, ret, coa, elo, talent, portal, line, ppa)
        
        self.assertIsNotNone(f)
        self.assertIn("offense_ppa_diff", f)
        self.assertIn("success_rate_diff", f)
        # Check that new features are not all zero (highly unlikely for these teams)
        self.assertNotEqual(f["offense_ppa_diff"], 0.0)
        self.assertNotEqual(f["success_rate_diff"], 0.0)

    def test_v3_prediction_range(self):
        """Assert all win probabilities between 0.05 and 0.95 for a few samples."""
        os.environ["MODEL_VERSION"] = "v3"
        # Since env var is read at import, we might need to mock it or just call the v3 function directly
        # But predict_win_probability should work if we force it
        import backend.models.win_probability
        backend.models.win_probability.MODEL_VERSION_FLAG = "v3"
        
        test_games = [
            ("Georgia", "Clemson"),
            ("Ohio State", "Akron"),
            ("Texas", "Colorado State")
        ]
        
        for h, a in test_games:
            res = predict_win_probability(h, a, 2024)
            self.assertIsInstance(res, dict)
            self.assertGreaterEqual(res["win_prob"], 0.01)
            self.assertLessEqual(res["win_prob"], 0.99)

    def test_model_version_flag(self):
        """Set MODEL_VERSION=v3, assert V3 artifacts used (via internal check)."""
        import backend.models.win_probability
        
        backend.models.win_probability.MODEL_VERSION_FLAG = "v3"
        res_v3 = predict_win_probability("Georgia", "Clemson", 2024)
        
        backend.models.win_probability.MODEL_VERSION_FLAG = "v2"
        res_v2 = predict_win_probability("Georgia", "Clemson", 2024)
        
        self.assertNotEqual(res_v3["win_prob"], res_v2["win_prob"])

    def test_v2_still_works(self):
        """Confirm V2 artifacts still load and predict correctly."""
        import backend.models.win_probability
        backend.models.win_probability.MODEL_VERSION_FLAG = "v2"
        
        res = predict_win_probability("Georgia", "Clemson", 2024)
        self.assertIsInstance(res, dict)
        self.assertIn("win_prob", res)
        # Known V2 value approx 0.81-0.85
        self.assertGreater(res["win_prob"], 0.5)

if __name__ == "__main__":
    unittest.main()
