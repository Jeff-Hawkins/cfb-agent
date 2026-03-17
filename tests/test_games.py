"""Tests for GET /games/weekly endpoint.

Covers:
  - Returns 200 with valid season/week
  - Response is sorted by model_edge descending
  - Returns empty list when no FBS games exist for the week
  - Low win probability games are filtered out (< 55% on both sides)
  - No auth required
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


def _games_df(rows=None):
    """Build a games DataFrame matching the /games/weekly query shape."""
    cols = ["id", "homeTeam", "awayTeam", "homePoints", "awayPoints", "neutralSite", "completed"]
    if rows is None:
        rows = [("1001", "Alabama", "Auburn", "", "", False, False)]
    return pd.DataFrame(rows, columns=cols)


def _lines_df(rows=None):
    """Build a betting_lines DataFrame."""
    cols = ["game_id", "spread"]
    if rows is None:
        rows = [("1001", -14.0)]
    return pd.DataFrame(rows, columns=cols)


def _picks_df(rows=None):
    """Build a picks DataFrame with approved pick info."""
    cols = ["game_id", "pick_team"]
    rows = rows or []
    return pd.DataFrame(rows, columns=cols)


def _mock_batch(home_win_prob: float):
    """Return a side_effect function for predict_win_probability_batch.

    Takes the games list passed to the batch function and enriches each dict
    with fixed win probabilities, mirroring the real function's output shape.
    """
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


class TestGetWeeklyGames(unittest.TestCase):
    @patch("routers.games.query_db")
    @patch("models.win_probability.predict_win_probability_batch",
           side_effect=_mock_batch(0.72))
    def test_returns_200_with_valid_params(self, mock_batch, mock_qdb):
        """GET /games/weekly with valid season/week returns HTTP 200."""
        mock_qdb.side_effect = [_games_df(), _lines_df(), _picks_df()]
        response = client.get("/games/weekly?season=2025&week=1")
        self.assertEqual(response.status_code, 200)

    @patch("routers.games.query_db")
    @patch("models.win_probability.predict_win_probability_batch",
           side_effect=_mock_batch(0.72))
    def test_sorted_by_model_edge_desc(self, mock_batch, mock_qdb):
        """Results should be ordered by model_edge descending."""
        games = pd.DataFrame([
            ("1001", "Alabama", "Auburn",  "", "", False, False),
            ("1002", "Georgia", "Florida", "", "", False, False),
        ], columns=["id", "homeTeam", "awayTeam", "homePoints", "awayPoints", "neutralSite", "completed"])

        # Alabama spread=-14 → home_implied=-6.16 → edge=abs(-14-(-6.16))=7.84
        # Georgia  spread=-7  → home_implied=-6.16 → edge=abs(-7-(-6.16))=0.84
        lines = pd.DataFrame([
            ("1001", -14.0),
            ("1002",  -7.0),
        ], columns=["game_id", "spread"])

        mock_qdb.side_effect = [games, lines, _picks_df()]
        response = client.get("/games/weekly?season=2025&week=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertGreaterEqual(data[0]["model_edge"], data[1]["model_edge"])

    @patch("routers.games.query_db")
    def test_returns_empty_list_for_no_games(self, mock_qdb):
        """No FBS games for the week should return []."""
        mock_qdb.return_value = pd.DataFrame(
            columns=["id", "homeTeam", "awayTeam", "homePoints", "awayPoints", "neutralSite", "completed"]
        )
        response = client.get("/games/weekly?season=2025&week=99")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    @patch("routers.games.query_db")
    @patch("models.win_probability.predict_win_probability_batch",
           side_effect=_mock_batch(0.52))
    def test_low_win_prob_game_filtered(self, mock_batch, mock_qdb):
        """Games where both sides have win_prob < 55% should be excluded."""
        # home=0.52, away=0.48 → neither >= 0.55 → filtered out
        mock_qdb.side_effect = [_games_df(), _lines_df(), _picks_df()]
        response = client.get("/games/weekly?season=2025&week=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    @patch("routers.games.query_db")
    @patch("models.win_probability.predict_win_probability_batch",
           side_effect=_mock_batch(0.72))
    def test_no_auth_required(self, mock_batch, mock_qdb):
        """GET /games/weekly should return 200 with no Authorization header."""
        mock_qdb.side_effect = [_games_df(), _lines_df(), _picks_df()]
        response = client.get("/games/weekly?season=2025&week=1", headers={})
        self.assertEqual(response.status_code, 200)

    @patch("routers.games.query_db")
    @patch("models.win_probability.predict_win_probability_batch",
           side_effect=_mock_batch(0.72))
    def test_has_approved_pick_flagged(self, mock_batch, mock_qdb):
        """Game with an approved pick should have has_approved_pick=true and pick_team set."""
        picks = _picks_df([("1001", "Alabama")])
        mock_qdb.side_effect = [_games_df(), _lines_df(), picks]
        response = client.get("/games/weekly?season=2025&week=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertTrue(data[0]["has_approved_pick"])
        self.assertEqual(data[0]["pick_team"], "Alabama")

    @patch("routers.games.query_db")
    @patch("models.win_probability.predict_win_probability_batch",
           side_effect=_mock_batch(0.72))
    def test_response_contains_expected_fields(self, mock_batch, mock_qdb):
        """Response objects must include all required fields."""
        mock_qdb.side_effect = [_games_df(), _lines_df(), _picks_df()]
        response = client.get("/games/weekly?season=2025&week=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        game = data[0]
        required = {
            "game_id", "season", "week", "home_team", "away_team",
            "home_win_prob", "away_win_prob",
            "home_implied_spread", "away_implied_spread",
            "consensus_spread", "model_edge",
            "has_approved_pick", "pick_team",
            "home_score", "away_score", "status",
        }
        self.assertTrue(required.issubset(set(game.keys())))


if __name__ == "__main__":
    unittest.main()
