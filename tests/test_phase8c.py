"""Tests for Phase 8C — Games page cleanup verification.

Covers:
  - /games/weekly response still includes model fields (kept in API, removed from UI)
  - /games/weekly response does NOT include sp_home or sp_away (frontend omits SP+ row)
  - /games/weekly returns 200 for valid params
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


def _games_df():
    cols = [
        "id", "homeTeam", "awayTeam", "homePoints", "awayPoints",
        "neutralSite", "completed", "homeConference", "awayConference",
        "homeClassification", "awayClassification",
    ]
    rows = [("2001", "Ohio State", "Michigan", "", "", False, False, "Big Ten", "Big Ten", "fbs", "fbs")]
    return pd.DataFrame(rows, columns=cols)


def _lines_df():
    return pd.DataFrame([("2001", -7.0)], columns=["game_id", "spread"])


def _picks_df():
    return pd.DataFrame([], columns=["game_id", "pick_team"])


def _mock_batch(home_win_prob: float):
    def _fn(games, season):
        return [
            {
                **g,
                "home_win_prob":     round(home_win_prob, 4),
                "away_win_prob":     round(1.0 - home_win_prob, 4),
                "raw_home_win_prob": round(home_win_prob, 4),
            }
            for g in games
        ]
    return _fn


class TestPhase8CAPIShape(unittest.TestCase):
    @patch("routers.games.query_db")
    @patch(
        "models.win_probability.predict_win_probability_batch",
        side_effect=_mock_batch(0.68),
    )
    def test_model_fields_still_present_in_response(self, mock_batch, mock_qdb):
        """API still returns model_edge and implied spreads even though UI no longer shows them."""
        mock_qdb.side_effect = [_games_df(), _lines_df(), _picks_df()]
        response = client.get("/games/weekly?season=2025&week=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        game = data[0]
        self.assertIn("model_edge", game)
        self.assertIn("home_implied_spread", game)
        self.assertIn("away_implied_spread", game)
        self.assertIn("has_approved_pick", game)

    @patch("routers.games.query_db")
    @patch(
        "models.win_probability.predict_win_probability_batch",
        side_effect=_mock_batch(0.68),
    )
    def test_sp_fields_absent_from_response(self, mock_batch, mock_qdb):
        """API does not include sp_home or sp_away — frontend omits SP+ row silently."""
        mock_qdb.side_effect = [_games_df(), _lines_df(), _picks_df()]
        response = client.get("/games/weekly?season=2025&week=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        game = data[0]
        self.assertNotIn("sp_home", game)
        self.assertNotIn("sp_away", game)

    @patch("routers.games.query_db")
    @patch(
        "models.win_probability.predict_win_probability_batch",
        side_effect=_mock_batch(0.68),
    )
    def test_win_prob_and_vegas_line_present(self, mock_batch, mock_qdb):
        """Core display fields — win probs and consensus spread — must be in response."""
        mock_qdb.side_effect = [_games_df(), _lines_df(), _picks_df()]
        response = client.get("/games/weekly?season=2025&week=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        game = data[0]
        self.assertIn("home_win_prob", game)
        self.assertIn("away_win_prob", game)
        self.assertIn("consensus_spread", game)
        self.assertIn("conference_group", game)
        self.assertIsNotNone(game["home_win_prob"])
        self.assertIsNotNone(game["consensus_spread"])

    @patch("routers.games.query_db")
    @patch(
        "models.win_probability.predict_win_probability_batch",
        side_effect=_mock_batch(0.68),
    )
    def test_conference_group_present(self, mock_batch, mock_qdb):
        """P4/G5 conference group must be present (badge still shown on UI)."""
        mock_qdb.side_effect = [_games_df(), _lines_df(), _picks_df()]
        response = client.get("/games/weekly?season=2025&week=1")
        data = response.json()
        self.assertEqual(data[0]["conference_group"], "P4")


if __name__ == "__main__":
    unittest.main()
