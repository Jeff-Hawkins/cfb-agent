"""Tests for tools/explanation_generator.py."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Repo root on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

FEATURE_COLS = [
    "home_rushingYards", "away_rushingYards", "diff_rushingYards",
    "home_turnovers", "away_turnovers", "diff_turnovers",
    "home_fumblesLost", "away_fumblesLost", "diff_fumblesLost",
    "sp_overall_diff", "sp_off_vs_def", "sp_def_vs_off", "sp_special_diff",
    "rec_3yr_diff", "ret_ppa_diff", "ret_pct_diff",
    "home_new_coach", "away_new_coach", "coach_win_pct_diff",
    "elo_diff", "talent_diff", "neutral_site", "home_field",
]


def _make_snapshot(home="Alabama", away="Auburn"):
    """Build a minimal feature snapshot dict for testing."""
    features = [
        {"name": col, "value": 0.0, "label": col, "description": col}
        for col in FEATURE_COLS
    ]
    return {
        "home_team": home,
        "away_team": away,
        "game_id": "1001",
        "season": 2024,
        "snapshot_timestamp": "2024-01-01T00:00:00+00:00",
        "features": features,
    }


class TestBuildFeatureSnapshotKeys(unittest.TestCase):
    """build_feature_snapshot returns a dict with the required top-level keys."""

    def test_build_feature_snapshot_keys(self):
        import pandas as pd

        empty_df = pd.DataFrame(columns=["year", "team", "rating", "offense_rating",
                                          "defense_rating", "specialTeams_rating"])
        empty_elo = pd.DataFrame(columns=["year", "team", "elo"])
        empty_rec = pd.DataFrame(columns=["year", "team", "points"])
        empty_ret = pd.DataFrame(columns=["year", "team", "ret_totalPPA", "ret_percentPPA"])
        empty_portal = pd.DataFrame(columns=["year", "team", "net_portal_score"])
        empty_talent = pd.DataFrame(columns=["year", "team", "talent"])
        empty_coaches = pd.DataFrame(columns=["school", "year", "firstName", "lastName",
                                               "wins", "losses", "games"])
        empty_stats = pd.DataFrame(columns=["season", "team", "statName", "statValue"])
        import joblib
        feature_cols_list = FEATURE_COLS

        side_effects = [
            empty_df, empty_elo, empty_rec, empty_ret,
            empty_portal, empty_talent, empty_coaches, empty_stats,
        ]

        with patch("tools.explanation_generator.query_db", side_effect=side_effects), \
             patch("joblib.load", return_value=feature_cols_list):
            from tools.explanation_generator import build_feature_snapshot
            result = build_feature_snapshot("Alabama", "Auburn", "1001", 2024)

        required_keys = {"home_team", "away_team", "game_id", "season",
                         "snapshot_timestamp", "features"}
        self.assertTrue(required_keys.issubset(result.keys()))
        self.assertIsInstance(result["features"], list)


class TestFeatureDescriptionsComplete(unittest.TestCase):
    """FEATURE_DESCRIPTIONS must have an entry for every feature in feature_cols."""

    def test_feature_descriptions_complete(self):
        from tools.explanation_generator import FEATURE_DESCRIPTIONS
        for col in FEATURE_COLS:
            self.assertIn(
                col, FEATURE_DESCRIPTIONS,
                f"FEATURE_DESCRIPTIONS is missing entry for '{col}'",
            )


class TestGenerateShortMocked(unittest.TestCase):
    """generate_explanation_short returns a non-empty string when Groq succeeds."""

    def test_generate_short_mocked(self):
        mock_choice = MagicMock()
        mock_choice.message.content = "Alabama has a strong SP+ edge at +8.2. The model projects 71% win probability driven by offensive dominance. Lean Alabama."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("tools.explanation_generator.os.getenv", return_value="fake-key"), \
             patch("groq.Groq", return_value=mock_client):
            from tools.explanation_generator import generate_explanation_short
            result = generate_explanation_short(_make_snapshot(), 0.71, -7.0, "Alabama")

        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


class TestGenerateFullMocked(unittest.TestCase):
    """generate_explanation_full returns a non-empty string when Groq succeeds."""

    def test_generate_full_mocked(self):
        mock_choice = MagicMock()
        mock_choice.message.content = (
            "Alabama's SP+ overall differential of +12.4 is the primary driver here. "
            "The home offense vs away defense matchup shows a +9.1 edge. "
            "Recruiting advantage of +45 points compounds over the roster. "
            "At -7, the model implies a -9.8 spread—nearly 3 points of value. "
            "The main risk is Auburn's returning production edge at +0.3 PPA."
        )
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("tools.explanation_generator.os.getenv", return_value="fake-key"), \
             patch("groq.Groq", return_value=mock_client):
            from tools.explanation_generator import generate_explanation_full
            result = generate_explanation_full(_make_snapshot(), 0.71, -7.0, "Alabama")

        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


class TestGroqFallback(unittest.TestCase):
    """When Groq raises an exception both generators return a non-empty fallback string."""

    def test_groq_fallback_short(self):
        with patch("groq.Groq", side_effect=Exception("API error")):
            from tools.explanation_generator import generate_explanation_short
            result = generate_explanation_short(_make_snapshot(), 0.71, -7.0, "Alabama")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_groq_fallback_full(self):
        with patch("groq.Groq", side_effect=Exception("API error")):
            from tools.explanation_generator import generate_explanation_full
            result = generate_explanation_full(_make_snapshot(), 0.71, -7.0, "Alabama")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


if __name__ == "__main__":
    unittest.main()
