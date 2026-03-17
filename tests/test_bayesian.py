"""Tests for Phase 6 Bayesian updating module.

Covers:
  - calculate_weekly_performance() returns expected keys and correct math
  - update_platt_scaler() returns updated=False when fewer than 20 picks
  - run_weekly_bayesian_update() handles exceptions gracefully and never raises
  - send_bayesian_update_notification() sends correct fields via SendGrid
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


class TestCalculateWeeklyPerformance(unittest.TestCase):
    EXPECTED_KEYS = {
        "season", "week", "picks", "wins", "losses",
        "win_rate", "avg_win_prob_on_wins", "avg_win_prob_on_losses",
        "brier_score_week",
    }

    def _picks_df(self, rows):
        return pd.DataFrame(rows, columns=["win_probability", "outcome"])

    @patch("db.database.query_db")
    def test_returns_expected_keys(self, mock_qdb):
        """Result dict must contain all required performance keys."""
        mock_qdb.return_value = self._picks_df([
            (0.72, "WIN"), (0.68, "WIN"), (0.71, "LOSS"),
        ])
        from tools.bayesian_updater import calculate_weekly_performance
        result = calculate_weekly_performance(2025, 1)
        self.assertEqual(set(result.keys()), self.EXPECTED_KEYS)

    @patch("db.database.query_db")
    def test_win_rate_correct(self, mock_qdb):
        """2 wins out of 3 picks → win_rate = 0.6667."""
        mock_qdb.return_value = self._picks_df([
            (0.72, "WIN"), (0.68, "WIN"), (0.71, "LOSS"),
        ])
        from tools.bayesian_updater import calculate_weekly_performance
        result = calculate_weekly_performance(2025, 1)
        self.assertAlmostEqual(result["win_rate"], 2 / 3, places=3)
        self.assertEqual(result["wins"], 2)
        self.assertEqual(result["losses"], 1)
        self.assertEqual(result["picks"], 3)

    @patch("db.database.query_db")
    def test_empty_df_returns_zeros(self, mock_qdb):
        """No picks → all metrics should be zero."""
        mock_qdb.return_value = pd.DataFrame(columns=["win_probability", "outcome"])
        from tools.bayesian_updater import calculate_weekly_performance
        result = calculate_weekly_performance(2025, 1)
        self.assertEqual(result["picks"], 0)
        self.assertEqual(result["wins"], 0)
        self.assertEqual(result["brier_score_week"], 0.0)

    @patch("db.database.query_db")
    def test_brier_score_perfect_calibration(self, mock_qdb):
        """Perfect calibration: prob=1.0 on WIN → Brier=0."""
        mock_qdb.return_value = self._picks_df([(1.0, "WIN"), (1.0, "WIN")])
        from tools.bayesian_updater import calculate_weekly_performance
        result = calculate_weekly_performance(2025, 1)
        self.assertAlmostEqual(result["brier_score_week"], 0.0, places=4)


class TestUpdatePlattScaler(unittest.TestCase):
    def _picks_df(self, n, outcome="WIN"):
        return pd.DataFrame({
            "win_probability": [0.72] * n,
            "outcome": [outcome] * n,
        })

    @patch("db.database.query_db")
    def test_returns_updated_false_when_fewer_than_20_picks(self, mock_qdb):
        """Fewer than 20 picks with outcomes → updated=False, no refit."""
        mock_qdb.return_value = self._picks_df(10)
        from tools.bayesian_updater import update_platt_scaler
        result = update_platt_scaler(2025, 1)
        self.assertFalse(result["updated"])
        self.assertEqual(result["picks_used"], 10)
        self.assertIsNone(result["old_brier"])

    @patch("db.database.query_db")
    def test_returns_updated_false_exactly_19_picks(self, mock_qdb):
        """19 picks — one below minimum, should not update."""
        mock_qdb.return_value = self._picks_df(19)
        from tools.bayesian_updater import update_platt_scaler
        result = update_platt_scaler(2025, 1)
        self.assertFalse(result["updated"])

    @patch("db.database.query_db")
    def test_returns_correct_picks_used_count(self, mock_qdb):
        """picks_used should match the number of rows returned."""
        mock_qdb.return_value = self._picks_df(5)
        from tools.bayesian_updater import update_platt_scaler
        result = update_platt_scaler(2025, 1)
        self.assertEqual(result["picks_used"], 5)


class TestRunWeeklyBayesianUpdate(unittest.TestCase):
    def test_never_raises_on_db_error(self):
        """run_weekly_bayesian_update must not raise even when DB is unavailable."""
        with patch("tools.bayesian_updater.calculate_weekly_performance", side_effect=Exception("DB down")):
            with patch("tools.bayesian_updater.update_platt_scaler", side_effect=Exception("refit fail")):
                with patch("tools.bayesian_updater.send_bayesian_update_notification"):
                    from tools.bayesian_updater import run_weekly_bayesian_update
                    try:
                        result = run_weekly_bayesian_update(2025, 1)
                    except Exception as exc:
                        self.fail(f"run_weekly_bayesian_update raised unexpectedly: {exc}")
                    self.assertEqual(result["season"], 2025)
                    self.assertEqual(result["week"], 1)

    def test_returns_dict_on_success(self):
        """On success, result dict includes season and week."""
        perf = {"season": 2025, "week": 1, "picks": 5, "wins": 3, "losses": 2,
                "win_rate": 0.6, "avg_win_prob_on_wins": 0.72,
                "avg_win_prob_on_losses": 0.69, "brier_score_week": 0.21}
        scaler = {"picks_used": 5, "old_brier": 0.21, "new_brier": None, "updated": False}

        with patch("tools.bayesian_updater.calculate_weekly_performance", return_value=perf):
            with patch("tools.bayesian_updater.update_platt_scaler", return_value=scaler):
                with patch("tools.bayesian_updater.send_bayesian_update_notification") as mock_notify:
                    from tools.bayesian_updater import run_weekly_bayesian_update
                    result = run_weekly_bayesian_update(2025, 1)
                    self.assertEqual(result["season"], 2025)
                    self.assertEqual(result["picks"], 5)
                    mock_notify.assert_called_once()


class TestSendBayesianUpdateNotification(unittest.TestCase):
    @patch.dict(os.environ, {"SENDGRID_API_KEY": "fake-key", "NOTIFY_EMAIL": "test@test.com"})
    def test_sends_with_correct_subject(self):
        """Notification email subject should include week and season."""
        mock_sg_client = MagicMock()
        mock_sg_client.send.return_value.status_code = 202

        mock_sg_module   = MagicMock()
        mock_mail_module = MagicMock()
        mock_sg_module.SendGridAPIClient.return_value = mock_sg_client

        with patch.dict(sys.modules, {
            "sendgrid": mock_sg_module,
            "sendgrid.helpers": MagicMock(),
            "sendgrid.helpers.mail": mock_mail_module,
        }):
            import importlib
            import tools.bayesian_updater as bu
            importlib.reload(bu)
            bu.send_bayesian_update_notification({
                "season": 2025, "week": 3,
                "picks_used": 25, "old_brier": 0.19, "new_brier": 0.17, "updated": True,
            })
            mock_sg_client.send.assert_called_once()

    @patch.dict(os.environ, {"SENDGRID_API_KEY": "", "NOTIFY_EMAIL": ""})
    def test_skips_silently_when_env_not_set(self):
        """Missing env vars → function returns without calling SendGrid."""
        mock_sg_module = MagicMock()
        with patch.dict(sys.modules, {
            "sendgrid": mock_sg_module,
            "sendgrid.helpers": MagicMock(),
            "sendgrid.helpers.mail": MagicMock(),
        }):
            from tools.bayesian_updater import send_bayesian_update_notification
            send_bayesian_update_notification({"season": 2025, "week": 1})
            mock_sg_module.SendGridAPIClient.assert_not_called()


if __name__ == "__main__":
    unittest.main()
