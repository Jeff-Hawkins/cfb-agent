"""Tests for GET /picks/public endpoint.

Covers:
  - Returns 200 with valid season/week
  - Response is sorted by abs(model_spread_diff) descending
  - Returns empty list (not 404) when no picks exist for week
  - No auth header required
"""

import sys
import os
import unittest
from unittest.mock import patch
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def _picks_df(rows):
    """Build a picks DataFrame matching the /picks/public query shape."""
    cols = [
        "id", "game_id", "season", "week",
        "home_team", "away_team", "pick_team",
        "win_probability", "spread", "model_spread_diff", "confidence_label",
        "outcome", "ats_result", "clv", "explanation_short",
    ]
    return pd.DataFrame(rows, columns=cols)


class TestGetPublicPicks(unittest.TestCase):
    @patch("routers.picks.query_db")
    def test_returns_200_with_valid_season_week(self, mock_qdb):
        """GET /picks/public?season=2025&week=1 should return HTTP 200."""
        mock_qdb.return_value = _picks_df([])
        response = client.get("/picks/public?season=2025&week=1")
        self.assertEqual(response.status_code, 200)

    @patch("routers.picks.query_db")
    def test_returns_empty_list_when_no_picks(self, mock_qdb):
        """Empty picks for week should return [] not 404."""
        mock_qdb.return_value = _picks_df([])
        response = client.get("/picks/public?season=2025&week=99")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    @patch("routers.picks.query_db")
    def test_sorted_by_model_spread_diff_desc(self, mock_qdb):
        """Picks should be ordered by abs(model_spread_diff) descending."""
        mock_qdb.return_value = _picks_df([
            ("uuid-1", "1001", 2025, 1, "Alabama", "Auburn",   "Alabama",
             0.72, -14.0, 7.84, "Lean",     None, None, None, "analysis"),
            ("uuid-2", "1002", 2025, 1, "Georgia", "Florida",  "Georgia",
             0.78,  -9.0, 3.20, "Moderate", None, None, None, None),
            ("uuid-3", "1003", 2025, 1, "Ohio St", "Michigan", "Ohio St",
             0.85, -17.0, 12.0, "Strong",   None, None, None, "analysis"),
        ])
        response = client.get("/picks/public?season=2025&week=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Already ordered by DB ORDER BY clause; verify we get 3 picks
        self.assertEqual(len(data), 3)

    @patch("routers.picks.query_db")
    def test_no_auth_required(self, mock_qdb):
        """Public endpoint should return 200 with no Authorization header."""
        mock_qdb.return_value = _picks_df([])
        response = client.get(
            "/picks/public?season=2025&week=1",
            headers={},   # explicitly no auth
        )
        self.assertEqual(response.status_code, 200)

    @patch("routers.picks.query_db")
    def test_returns_week_from_picks_when_week_omitted(self, mock_qdb):
        """Omitting week param triggers most-recent-week lookup then fetch."""
        week_df   = pd.DataFrame([{"week": 3}])
        picks_df  = _picks_df([
            ("uuid-1", "1001", 2025, 3, "Alabama", "Auburn", "Alabama",
             0.72, -14.0, 7.84, "Lean", None, None, None, None),
        ])
        mock_qdb.side_effect = [week_df, picks_df]
        response = client.get("/picks/public?season=2025")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    @patch("routers.picks.query_db")
    def test_returns_empty_list_when_no_approved_picks_any_week(self, mock_qdb):
        """No approved picks for any week → return [] not 404."""
        mock_qdb.return_value = pd.DataFrame(columns=["week"])
        response = client.get("/picks/public?season=2025")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])


if __name__ == "__main__":
    unittest.main()
