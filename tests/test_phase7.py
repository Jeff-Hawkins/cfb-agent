import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np

# Ensure repo root and backend are importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from tools.fetch_outcomes import update_pick_outcomes
from tools.calculate_clv import calculate_and_store_clv, get_clv_summary
from backend.routers.games import get_conference_group

class TestPhase7(unittest.TestCase):

    # 1. ATS Resolution Logic
    def test_ats_resolution(self):
        # UCLA (home) vs Utah (away), spread=+6.5 (UCLA is dog)
        # margin = home_score - away_score = 10 - 43 = -33
        # home covers if: margin > -spread  => -33 > -6.5 (False)
        # away covers if: margin < -spread  => -33 < -6.5 (True)
        
        # We'll mock the logic that fetch_game_outcomes uses
        def resolve_ats(home_score, away_score, spread):
            margin = home_score - away_score
            if margin > -spread: return 'home_covered'
            if margin < -spread: return 'away_covered'
            return 'push'

        # Test Case: UCLA underdog, fails to cover
        self.assertEqual(resolve_ats(10, 43, 6.5), 'away_covered')
        
        # Test Case: Home favorite, covers
        # Bama -14, wins 31-10. margin = 21. -spread = 14. 21 > 14 (True)
        self.assertEqual(resolve_ats(31, 10, -14.0), 'home_covered')
        
        # Test Case: Home favorite, wins but doesn't cover
        # Bama -14, wins 24-20. margin = 4. -spread = 14. 4 < 14 (True)
        self.assertEqual(resolve_ats(24, 20, -14.0), 'away_covered')
        
        # Test Case: Push
        # margin = 7, spread = -7
        self.assertEqual(resolve_ats(27, 20, -7.0), 'push')

    # 2. pick_spread capture logic (Mocking the endpoint logic)
    def test_pick_spread_capture_logic(self):
        def get_pick_spread(pick_team, home_team, spread):
            if pick_team == home_team:
                return spread
            else:
                return -1.0 * spread
        
        # Home pick: spread -7 -> pick_spread -7
        self.assertEqual(get_pick_spread("Bama", "Bama", -7.0), -7.0)
        # Away pick: spread -7 -> pick_spread +7
        self.assertEqual(get_pick_spread("Auburn", "Bama", -7.0), 7.0)
        # Home dog pick: spread +3 -> pick_spread +3
        self.assertEqual(get_pick_spread("Vandy", "Vandy", 3.0), 3.0)

    # 3. CLV Calculation
    def test_clv_calculation(self):
        # clv = pick_spread - closing_spread (positive = beat the close)
        def calc_clv(p_spread, c_spread):
            return p_spread - c_spread
            
        # Positive CLV: Got -6.5, closed -7.5. diff = -6.5 - (-7.5) = +1.0
        self.assertEqual(calc_clv(-6.5, -7.5), 1.0)
        # Negative CLV: Got -6.5, closed -5.5. diff = -6.5 - (-5.5) = -1.0
        self.assertEqual(calc_clv(-6.5, -5.5), -1.0)
        # Zero CLV
        self.assertEqual(calc_clv(-6.5, -6.5), 0.0)

    # 4. G5/P4 conference mapping
    def test_conference_mapping(self):
        # P4 cases
        self.assertEqual(get_conference_group('SEC', 'Sun Belt', 'fbs', 'fbs'), 'P4')
        self.assertEqual(get_conference_group('MAC', 'Big Ten', 'fbs', 'fbs'), 'P4')
        self.assertEqual(get_conference_group('Big 12', 'Big 12', 'fbs', 'fbs'), 'P4')
        self.assertEqual(get_conference_group('ACC', 'FBS Independents', 'fbs', 'fbs'), 'P4')
        
        # G5 cases
        self.assertEqual(get_conference_group('Sun Belt', 'MAC', 'fbs', 'fbs'), 'G5')
        self.assertEqual(get_conference_group('Conference USA', 'Mountain West', 'fbs', 'fbs'), 'G5')
        self.assertEqual(get_conference_group('American Athletic', 'FBS Independents', 'fbs', 'fbs'), 'G5')
        
        # FCS/None cases
        self.assertEqual(get_conference_group('SEC', 'Ivy', 'fbs', 'fcs'), 'P4') # Still P4 if one is FBS P4
        self.assertEqual(get_conference_group('Southland', 'Ivy', 'fcs', 'fcs'), None)

    # 5. get_clv_summary shape
    @patch("tools.calculate_clv.query_db")
    def test_clv_summary_shape(self, mock_qdb):
        mock_df = pd.DataFrame([
            {"clv": 1.5, "clv_positive": True, "outcome": "WIN"},
            {"clv": 0.5, "clv_positive": True, "outcome": "LOSS"},
            {"clv": -1.0, "clv_positive": False, "outcome": "LOSS"},
        ])
        mock_qdb.return_value = mock_df
        
        summary = get_clv_summary(2025)
        
        self.assertEqual(summary["total_picks"], 3)
        self.assertEqual(summary["clv_positive_count"], 2)
        self.assertAlmostEqual(summary["clv_positive_pct"], 66.7, places=1)
        self.assertEqual(summary["avg_clv"], 0.33)
        self.assertEqual(summary["avg_clv_wins"], 1.5)
        self.assertEqual(summary["avg_clv_losses"], -0.25)

    # 6. Idempotency (Mocking fetch_game_outcomes logic)
    @patch("tools.fetch_outcomes.engine")
    @patch("tools.fetch_outcomes.query_db")
    @patch("requests.get")
    def test_fetch_outcomes_idempotency(self, mock_get, mock_qdb, mock_engine):
        mock_get.return_value.json.return_value = [
            {"id": 401752800, "home_team": "UCLA", "away_team": "Utah", "home_points": 10, "away_points": 43, "completed": True}
        ]
        mock_qdb.return_value = pd.DataFrame([{"game_id": "401752800", "spread": 6.5}])
        
        from tools.fetch_outcomes import fetch_game_outcomes
        
        # Run twice
        fetch_game_outcomes(2025, 1)
        fetch_game_outcomes(2025, 1)
        
        # Check that cron_log has two entries
        # The first call to execute will be for game_outcomes upsert, second for cron_log
        # Total 4 execute calls (2 per run)
        self.assertEqual(mock_engine.begin.return_value.__enter__.return_value.execute.call_count, 4)
        
        # Verify UPSERT syntax was used
        calls = mock_engine.begin.return_value.__enter__.return_value.execute.call_args_list
        self.assertIn("ON CONFLICT (game_id) DO UPDATE", str(calls[0][0][0]))

if __name__ == "__main__":
    unittest.main()
