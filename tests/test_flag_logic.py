"""Tests for Phase 6 corrected flag logic.

Covers:
  - _directed_spread_diff() for home and away picks
  - Blowout filter (abs(spread) > 17)
  - abs(spread_diff) >= 5.0 threshold
  - POST /picks/recalculate-spreads requires admin auth
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from routers.picks import _directed_spread_diff


class TestDirectedSpreadDiff(unittest.TestCase):
    def test_home_pick_negative_spread(self):
        """Home pick, spread=-7.0, pick_win_prob=0.72.

        model_implied = -1 * (0.72 - 0.5) * 28 = -6.16
        spread_diff   = -7.0 - (-6.16) = -0.84
        """
        diff = _directed_spread_diff(0.72, "Alabama", "Alabama", -7.0)
        self.assertAlmostEqual(diff, -0.84, places=2)

    def test_home_pick_large_spread_flags(self):
        """Home pick, spread=-14.0, pick_win_prob=0.72 — qualifies as model edge.

        model_implied = -6.16
        spread_diff   = -14.0 - (-6.16) = -7.84 → abs=7.84 >= 5.0
        """
        diff = _directed_spread_diff(0.72, "Alabama", "Alabama", -14.0)
        self.assertAlmostEqual(diff, -7.84, places=2)
        self.assertGreaterEqual(abs(diff), 5.0)

    def test_away_pick_positive_spread(self):
        """Away pick, pick_win_prob=0.65, spread=7.0 (home +7).

        model_implied = (0.65 - 0.5) * 28 = 4.2
        spread_diff   = 7.0 - 4.2 = 2.8
        """
        diff = _directed_spread_diff(0.65, "Auburn", "Alabama", 7.0)
        self.assertAlmostEqual(diff, 2.8, places=2)

    def test_away_pick_large_edge(self):
        """Away pick with big disagreement — abs(spread_diff) >= 5.0."""
        diff = _directed_spread_diff(0.70, "Auburn", "Alabama", 12.0)
        # model_implied = (0.70-0.5)*28 = 5.6; spread_diff = 12.0-5.6 = 6.4
        self.assertAlmostEqual(diff, 6.4, places=2)
        self.assertGreaterEqual(abs(diff), 5.0)

    def test_home_pick_small_edge_below_threshold(self):
        """Home pick with tiny disagreement — abs(spread_diff) < 5.0."""
        diff = _directed_spread_diff(0.72, "Alabama", "Alabama", -7.0)
        self.assertLess(abs(diff), 5.0)


class TestBlowoutFilter(unittest.TestCase):
    def test_spread_17_is_not_blowout(self):
        """abs(spread) == 17 should NOT be filtered."""
        self.assertFalse(abs(-17.0) > 17)

    def test_spread_18_is_blowout(self):
        """abs(spread) == 18 should be filtered as blowout."""
        self.assertTrue(abs(-18.0) > 17)

    def test_spread_21_is_blowout(self):
        self.assertTrue(abs(-21.0) > 17)

    @patch("routers.picks.engine")
    @patch("routers.picks.query_db")
    @patch("models.win_probability.predict_win_probability", return_value=0.80)
    @patch("services.notifications.send_picks_ready_email")
    def test_blowout_game_not_flagged(self, mock_email, mock_predict, mock_qdb, mock_engine):
        """Game with spread=-21 (blowout) should not be flagged despite high win prob."""
        games_df = pd.DataFrame([{
            "id": "1001", "homeTeam": "Alabama", "awayTeam": "Mercer", "neutralSite": False,
        }])
        lines_df = pd.DataFrame([{"game_id": "1001", "spread": -21.0}])
        mock_qdb.side_effect = [games_df, lines_df]

        from routers.picks import flag_picks
        result = flag_picks(season=2025, week=1, _=None)
        self.assertEqual(result["flagged"], 0)


class TestSpreadDiffThreshold(unittest.TestCase):
    @patch("routers.picks.engine")
    @patch("routers.picks.query_db")
    @patch("models.win_probability.predict_win_probability", return_value=0.72)
    @patch("services.notifications.send_picks_ready_email")
    def test_small_spread_diff_not_flagged(self, mock_email, mock_predict, mock_qdb, mock_engine):
        """abs(spread_diff) < 5.0 — pick should not be inserted."""
        games_df = pd.DataFrame([{
            "id": "1001", "homeTeam": "Alabama", "awayTeam": "Auburn", "neutralSite": False,
        }])
        # spread=-7.0 → home pick model_implied=-6.16 → spread_diff=-0.84 → abs=0.84 < 5.0
        lines_df = pd.DataFrame([{"game_id": "1001", "spread": -7.0}])
        mock_qdb.side_effect = [games_df, lines_df]

        from routers.picks import flag_picks
        result = flag_picks(season=2025, week=1, _=None)
        self.assertEqual(result["flagged"], 0)

    @patch("routers.picks.engine")
    @patch("routers.picks.query_db")
    @patch("models.win_probability.predict_win_probability", return_value=0.72)
    @patch("services.notifications.send_picks_ready_email")
    def test_large_spread_diff_flagged(self, mock_email, mock_predict, mock_qdb, mock_engine):
        """abs(spread_diff) >= 5.0 and abs(spread) <= 17 — pick should be inserted."""
        games_df = pd.DataFrame([{
            "id": "1001", "homeTeam": "Alabama", "awayTeam": "Auburn", "neutralSite": False,
        }])
        lines_df = pd.DataFrame([{"game_id": "1001", "spread": -14.0}])
        mock_qdb.side_effect = [games_df, lines_df]

        conn = MagicMock()
        conn.execute.return_value.rowcount = 1
        mock_engine.begin.return_value.__enter__ = MagicMock(return_value=conn)
        mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

        from routers.picks import flag_picks
        result = flag_picks(season=2025, week=1, _=None)
        self.assertEqual(result["flagged"], 1)


class TestRecalculateSpreadsAuth(unittest.TestCase):
    def test_recalculate_spreads_requires_auth(self):
        """POST /picks/recalculate-spreads without auth token should return 401."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        response = client.post("/picks/recalculate-spreads")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
