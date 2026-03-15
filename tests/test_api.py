"""Integration tests for the FastAPI backend.

Uses FastAPI's TestClient (backed by httpx) to exercise the live endpoints
against the real database and trained model artifacts.
"""

import sys
import os

# Ensure repo root is on the path when running pytest from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_returns_200():
    """GET /health should return HTTP 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_matchup_valid_teams_returns_expected_keys():
    """GET /matchup with valid teams should return all expected response keys."""
    response = client.get("/matchup", params={"home": "Ohio State", "away": "Michigan", "season": 2024})
    assert response.status_code == 200
    data = response.json()
    assert "home_team" in data
    assert "away_team" in data
    assert "home_win_probability" in data
    assert "away_win_probability" in data
    assert "model_version" in data
    assert data["home_team"] == "Ohio State"
    assert data["away_team"] == "Michigan"
    assert 0.0 <= data["home_win_probability"] <= 1.0
    assert abs(data["home_win_probability"] + data["away_win_probability"] - 1.0) < 1e-6


def test_matchup_invalid_team_returns_404():
    """GET /matchup with an unknown team name should return HTTP 404."""
    response = client.get("/matchup", params={"home": "Fake University", "away": "Michigan", "season": 2024})
    assert response.status_code == 404
    assert "detail" in response.json()


def test_rankings_returns_at_least_100_teams():
    """GET /rankings should return a list of at least 100 teams with required fields."""
    response = client.get("/rankings")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 100
    first = data[0]
    assert "rank" in first
    assert "team" in first
    assert "composite_rating" in first
    assert first["rank"] == 1
