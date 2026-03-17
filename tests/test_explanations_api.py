"""Tests for the /explanations API router (backend/routers/explanations.py)."""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

# Ensure both repo root and backend are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

_NULL_UUID = "00000000-0000-0000-0000-000000000000"
_VALID_UUID = "11111111-1111-1111-1111-111111111111"


class TestGetExplanation404(unittest.TestCase):
    """GET /explanations/{pick_id} returns 404 when no explanation exists."""

    def test_get_explanation_404(self):
        with patch("routers.explanations.query_db", return_value=pd.DataFrame()):
            response = client.get(f"/explanations/{_NULL_UUID}")
        self.assertEqual(response.status_code, 404)
        self.assertIn("detail", response.json())


class TestGenerateRequiresAuth(unittest.TestCase):
    """POST /explanations/generate/{pick_id} without auth returns 401 or 403."""

    def test_generate_requires_auth(self):
        response = client.post(f"/explanations/generate/{_VALID_UUID}")
        # FastAPI HTTPBearer returns 403 when no credentials are provided
        self.assertIn(response.status_code, (401, 403))


class TestGenerateReturnsStructure(unittest.TestCase):
    """POST /explanations/generate/{pick_id} with valid auth returns explanation_short."""

    def test_generate_returns_structure(self):
        admin_key = "test-admin-key"
        mock_result = {
            "pick_id": _VALID_UUID,
            "explanation_short": "Alabama has a strong edge based on SP+ and Elo.",
            "explanation_full": "Full analysis here.",
            "feature_snapshot": {},
            "model_version": "2.0.0",
            "generated_at": "2024-01-01T00:00:00+00:00",
        }

        with patch.dict(os.environ, {"ADMIN_API_KEY": admin_key}), \
             patch(
                 "routers.explanations.generate_and_store_explanation",
                 return_value=mock_result,
             ):
            from routers import explanations as exp_module
            with patch.object(exp_module, "generate_and_store_explanation", return_value=mock_result):
                response = client.post(
                    f"/explanations/generate/{_VALID_UUID}",
                    headers={"Authorization": f"Bearer {admin_key}"},
                )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("explanation_short", data)


if __name__ == "__main__":
    unittest.main()
