# Testing Skill — cfb-agent

## Philosophy
No function ships without tests. Every module gets docstrings.
Tests live in `tests/`. Run with `pytest tests/` from repo root.

## Test File Conventions
- One test file per phase or module: `test_phase7.py`, `test_model_retrain.py`, `test_api.py`
- Test function names describe what they verify: `test_clv_calculation_positive`, `test_flag_thresholds_applied`
- Always test both happy path and edge cases

## Running Tests
```bash
# All tests
pytest tests/ -v

# Single file
pytest tests/test_api.py -v

# Single test
pytest tests/test_api.py::test_picks_endpoint -v
```

## API Tests (test_api.py)
Use TestClient from FastAPI:
```python
from fastapi.testclient import TestClient
from backend.main import app
client = TestClient(app)
```

## Model Tests
Always assert:
- Feature list length matches expected count exactly
- All features present and non-null for a known game
- Win probability output is between 0.05 and 0.95
- Calibrated model and raw model both load without error

## DB Tests
- Never test against production Supabase in CI
- Use mock or fixture data for unit tests
- Integration tests that hit the DB should be tagged and run manually

## Before Any Migration or Pipeline Change
Run full test suite and confirm pass before writing migration SQL.
Document which tests cover the affected tables/functions.

## Required Coverage Triggers
| Trigger | Action |
|---|---|
| New function written | Write test immediately, same session |
| Module completed | Add docstrings before committing |
| Before DB migration | Run full suite, confirm pass |
| Before model retrain | Confirm data pipeline tests pass |
