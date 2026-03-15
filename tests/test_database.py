"""Tests for db/database.py — connection, read/write, flatten_lists, and error handling.

Each test uses a dedicated temporary table (test_db_<name>) that is dropped in
a teardown fixture so the Supabase schema stays clean between runs.
"""

import pytest
import pandas as pd
from sqlalchemy import text

from db.database import engine, save_to_db, query_db, test_connection as db_test_connection


TEMP_TABLE = "test_db_temp"


@pytest.fixture(autouse=True)
def drop_temp_table():
    """Drop the temporary test table before and after every test."""
    with engine.connect() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {TEMP_TABLE}"))
        conn.commit()
    yield
    with engine.connect() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {TEMP_TABLE}"))
        conn.commit()


def test_connection_succeeds():
    """test_connection() should run SELECT 1 without raising an exception."""
    # If the connection fails, test_connection prints an error and the
    # underlying engine.connect() call will raise — we verify no exception.
    try:
        db_test_connection()
    except Exception as exc:
        pytest.fail(f"test_connection() raised unexpectedly: {exc}")


def test_save_and_query_roundtrip():
    """save_to_db() should persist rows that query_db() can read back exactly."""
    df = pd.DataFrame([
        {"name": "Alabama", "rating": 95.3},
        {"name": "Georgia", "rating": 91.7},
    ])
    save_to_db(df, TEMP_TABLE)

    result = query_db(f"SELECT name, rating FROM {TEMP_TABLE} ORDER BY name")

    assert len(result) == 2
    assert list(result["name"]) == ["Alabama", "Georgia"]
    assert abs(result["rating"].iloc[0] - 95.3) < 1e-6


def test_flatten_lists_serializes_complex_columns():
    """save_to_db() should coerce list and dict column values to strings via flatten_lists."""
    df = pd.DataFrame([
        {"team": "Ohio State", "metadata": {"conf": "Big Ten"}, "scores": [35, 28]},
    ])
    # Would raise if list/dict values were passed raw to PostgreSQL
    save_to_db(df, TEMP_TABLE)

    result = query_db(f"SELECT team, metadata, scores FROM {TEMP_TABLE}")

    assert len(result) == 1
    assert result["team"].iloc[0] == "Ohio State"
    # Values should have been stringified
    assert isinstance(result["metadata"].iloc[0], str)
    assert isinstance(result["scores"].iloc[0], str)


def test_query_db_raises_on_bad_sql():
    """query_db() should propagate a SQLAlchemy exception when given invalid SQL."""
    with pytest.raises(Exception):
        query_db("SELECT * FROM table_that_does_not_exist_xyz")
