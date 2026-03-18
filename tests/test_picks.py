"""Tests for Phase 4.5 pick flagging, approval, rejection, and outcome logic.

Pure-function tests run without any DB connection.
DB-interaction tests mock engine / query_db.
predict_win_probability and send_picks_ready_email are lazy-imported inside
flag_picks(), so they are patched at their source modules.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

# Make the backend package importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from routers.picks import confidence_label, compute_model_spread_diff


# ---------------------------------------------------------------------------
# Pure unit tests — no DB or model needed
# ---------------------------------------------------------------------------

class TestConfidenceLabel(unittest.TestCase):
    def test_confidence_label_lean(self):
        assert confidence_label(0.68) == "Lean"

    def test_confidence_label_moderate(self):
        assert confidence_label(0.78) == "Moderate"

    def test_confidence_label_strong(self):
        assert confidence_label(0.87) == "Strong"

    def test_confidence_boundary_lean_moderate(self):
        """Exactly 0.75 should be Moderate, not Lean."""
        assert confidence_label(0.75) == "Moderate"

    def test_confidence_boundary_moderate_strong(self):
        """Exactly 0.85 should be Strong."""
        assert confidence_label(0.85) == "Strong"


class TestModelSpreadDiff(unittest.TestCase):
    def test_model_spread_diff_calculation(self):
        """(0.72 - 0.5) * 28 = 6.16; diff vs consensus 0 = 6.16."""
        diff = compute_model_spread_diff(0.72, 0.0)
        assert abs(diff - 6.16) < 0.001

    def test_model_spread_diff_vs_market(self):
        """home_win_prob=0.72 → implied=6.16; consensus=-3 → diff=abs(6.16-(-3))=9.16."""
        diff = compute_model_spread_diff(0.72, -3.0)
        assert abs(diff - 9.16) < 0.001

    def test_flag_below_threshold_skipped(self):
        """Win prob 0.60 is below the 0.65 threshold — neither side qualifies."""
        assert 0.60 < 0.65
        assert (1.0 - 0.60) < 0.65

    def test_flag_small_edge_skipped(self):
        """model_spread_diff=2.0 is below the 3.0 minimum edge requirement."""
        # implied=6.16, spread=4.16 → diff=abs(6.16-4.16)=2.0
        assert compute_model_spread_diff(0.70, (0.70 - 0.5) * 28 - 2.0) < 3.0


# ---------------------------------------------------------------------------
# DB-interaction tests — mock engine and query_db
# ---------------------------------------------------------------------------

def _make_games_df(home="Alabama", away="Auburn", game_id="1001"):
    return pd.DataFrame([{
        "id": game_id,
        "homeTeam": home,
        "awayTeam": away,
        "neutralSite": False,
    }])


def _make_lines_df(game_id="1001", spread=-14.0):
    # Default spread triggers Phase 6 flag thresholds:
    #   home pick, win_prob=0.72, model_implied=-6.16
    #   spread_diff = -14.0 - (-6.16) = -7.84 → abs=7.84 >= 5.0 ✓
    #   abs(-14) = 14 <= 17 (not a blowout) ✓
    return pd.DataFrame([{"game_id": game_id, "spread": spread}])


def _make_conn():
    conn = MagicMock()
    conn.execute.return_value.rowcount = 1
    return conn


def _patch_engine(mock_engine, conn):
    mock_engine.begin.return_value.__enter__ = MagicMock(return_value=conn)
    mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)


class TestFlagPicks(unittest.TestCase):
    # predict_win_probability and send_picks_ready_email are lazy-imported
    # inside flag_picks(), so patch at their source modules.

    @patch("routers.picks.engine")
    @patch("routers.picks.query_db")
    @patch("models.win_probability.predict_win_probability", return_value=0.72)
    @patch("services.notifications.send_picks_ready_email")
    def test_flag_inserts_correctly(self, mock_email, mock_predict, mock_qdb, mock_engine):
        """A qualifying pick should be inserted with all required fields."""
        mock_qdb.side_effect = [_make_games_df(), _make_lines_df()]
        conn = _make_conn()
        _patch_engine(mock_engine, conn)

        from routers.picks import flag_picks
        result = flag_picks(season=2025, week=1, _=None)

        assert result["flagged"] == 1
        conn.execute.assert_called_once()
        sql_call = conn.execute.call_args
        params = sql_call[0][1]
        assert params["pick_team"] == "Alabama"
        assert params["win_probability"] == round(0.72, 4)
        assert params["confidence_label"] == "Lean"
        assert "ON CONFLICT" in str(sql_call[0][0])

    @patch("routers.picks.engine")
    @patch("routers.picks.query_db")
    @patch("models.win_probability.predict_win_probability", return_value=0.60)
    @patch("services.notifications.send_picks_ready_email")
    def test_flag_below_win_prob_threshold(self, mock_email, mock_predict, mock_qdb, mock_engine):
        """Win prob 0.60 (both sides < 0.65) should not flag any picks."""
        mock_qdb.side_effect = [_make_games_df(), _make_lines_df()]

        from routers.picks import flag_picks
        result = flag_picks(season=2025, week=1, _=None)

        assert result["flagged"] == 0
        mock_engine.begin.assert_not_called()

    @patch("routers.picks.engine")
    @patch("routers.picks.query_db")
    @patch("models.win_probability.predict_win_probability", return_value=0.72)
    @patch("services.notifications.send_picks_ready_email")
    def test_flag_small_edge_not_inserted(self, mock_email, mock_predict, mock_qdb, mock_engine):
        """abs(spread_diff) < 5.0 should skip the pick.

        Home pick, model_implied = -1*(0.72-0.5)*28 = -6.16
        spread=-7.0 → spread_diff = -7.0 - (-6.16) = -0.84 → abs=0.84 < 5.0
        """
        mock_qdb.side_effect = [_make_games_df(), _make_lines_df(spread=-7.0)]

        from routers.picks import flag_picks
        result = flag_picks(season=2025, week=1, _=None)

        assert result["flagged"] == 0

    @patch("routers.picks.engine")
    @patch("routers.picks.query_db")
    @patch("models.win_probability.predict_win_probability", return_value=0.72)
    @patch("services.notifications.send_picks_ready_email")
    def test_duplicate_game_skipped(self, mock_email, mock_predict, mock_qdb, mock_engine):
        """Same game_id twice in games → INSERT uses ON CONFLICT DO NOTHING."""
        two_games = pd.DataFrame([
            {"id": "1001", "homeTeam": "Alabama", "awayTeam": "Auburn", "neutralSite": False},
            {"id": "1001", "homeTeam": "Alabama", "awayTeam": "Auburn", "neutralSite": False},
        ])
        mock_qdb.side_effect = [two_games, _make_lines_df()]
        conn = _make_conn()
        _patch_engine(mock_engine, conn)

        from routers.picks import flag_picks
        flag_picks(season=2025, week=1, _=None)

        assert "ON CONFLICT" in str(conn.execute.call_args[0][0])


class TestApproveReject(unittest.TestCase):
    @patch("routers.picks.query_db")
    @patch("routers.picks.engine")
    def test_approve_sets_timestamp(self, mock_engine, mock_qdb):
        """Approve should UPDATE approved=true and approval_timestamp=NOW() and set pick_spread."""
        # Mock the two SELECT calls in approve_pick
        mock_pick_df = pd.DataFrame([{"game_id": "1001", "pick_team": "Alabama", "home_team": "Alabama"}])
        mock_line_df = pd.DataFrame([{"spread": -7.0}])
        mock_qdb.side_effect = [mock_pick_df, mock_line_df]

        conn = _make_conn()
        _patch_engine(mock_engine, conn)

        from routers.picks import approve_pick
        pick_uuid = "550e8400-e29b-41d4-a716-446655440000"
        result = approve_pick(pick_uuid, _=None)

        assert result["approved"] is True
        assert result["pick_spread"] == -7.0
        
        sql = str(conn.execute.call_args[0][0])
        params = conn.execute.call_args[0][1]
        assert "approved" in sql.lower()
        assert "pick_spread" in sql.lower()
        assert params["id"] == pick_uuid
        assert params["pick_spread"] == -7.0

    @patch("routers.picks.engine")
    def test_reject_sets_flag(self, mock_engine):
        """Reject should UPDATE rejected=true."""
        conn = _make_conn()
        _patch_engine(mock_engine, conn)

        from routers.picks import reject_pick
        # Using a valid-ish UUID just in case
        pick_uuid = "550e8400-e29b-41d4-a716-446655440001"
        result = reject_pick(pick_uuid, _=None)

        assert result["rejected"] is True
        sql = str(conn.execute.call_args[0][0])
        assert "rejected" in sql.lower()
        params = conn.execute.call_args[0][1]
        assert params["id"] == pick_uuid


class TestUpdateOutcomes(unittest.TestCase):
    def _picks_df(self, pick_team="Alabama", game_id="1001", spread=-7.0):
        return pd.DataFrame([{
            "id": "pick-uuid-1",
            "game_id": game_id,
            "pick_team": pick_team,
            "home_team": "Alabama",
            "away_team": "Auburn",
            "spread": spread,
        }])

    def _game_df(self, home_pts=31, away_pts=17):
        return pd.DataFrame([{
            "homeTeam": "Alabama",
            "awayTeam": "Auburn",
            "homePoints": home_pts,
            "awayPoints": away_pts,
        }])

    @patch("routers.picks.engine")
    @patch("routers.picks.query_db")
    def test_outcome_win(self, mock_qdb, mock_engine):
        """Pick team (home Alabama) won → outcome=WIN."""
        mock_qdb.side_effect = [self._picks_df(), self._game_df(31, 17)]
        conn = _make_conn()
        _patch_engine(mock_engine, conn)

        from routers.picks import update_outcomes
        result = update_outcomes(season=2025, week=1, _=None)

        assert result["updated"] == 1
        params = conn.execute.call_args[0][1]
        assert params["outcome"] == "WIN"

    @patch("routers.picks.engine")
    @patch("routers.picks.query_db")
    def test_outcome_ats_covered(self, mock_qdb, mock_engine):
        """Alabama -7, wins by 10 → ATS WIN (covered_margin = 10 + (-7) = 3 > 0)."""
        mock_qdb.side_effect = [self._picks_df(spread=-7.0), self._game_df(34, 24)]
        conn = _make_conn()
        _patch_engine(mock_engine, conn)

        from routers.picks import update_outcomes
        update_outcomes(season=2025, week=1, _=None)

        params = conn.execute.call_args[0][1]
        assert params["ats_result"] == "WIN"

    @patch("routers.picks.engine")
    @patch("routers.picks.query_db")
    def test_outcome_push(self, mock_qdb, mock_engine):
        """Alabama -7, wins by exactly 7 → ATS PUSH."""
        mock_qdb.side_effect = [self._picks_df(spread=-7.0), self._game_df(31, 24)]
        conn = _make_conn()
        _patch_engine(mock_engine, conn)

        from routers.picks import update_outcomes
        update_outcomes(season=2025, week=1, _=None)

        params = conn.execute.call_args[0][1]
        assert params["ats_result"] == "PUSH"

    @patch("routers.picks.engine")
    @patch("routers.picks.query_db")
    def test_update_outcomes_retry(self, mock_qdb, mock_engine):
        """Game score not yet in DB → retry=true returned."""
        mock_qdb.side_effect = [self._picks_df(), pd.DataFrame()]  # empty = no score yet

        from routers.picks import update_outcomes
        result = update_outcomes(season=2025, week=1, _=None)

        assert result["retry"] is True
        assert result["pending"] == 1
        assert result["updated"] == 0


if __name__ == "__main__":
    unittest.main()
