import os
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
)


def flatten_lists(df: pd.DataFrame) -> pd.DataFrame:
    """Convert any list or dict column values to strings to prevent serialization errors."""
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, (list, dict))).any():
            df[col] = df[col].apply(lambda x: str(x) if isinstance(x, (list, dict)) else x)
    return df


def save_to_db(df: pd.DataFrame, table_name: str):
    """Flatten and append a DataFrame to the specified database table.

    Args:
        df: DataFrame to save.
        table_name: Target table name. Created if it does not exist; rows are appended.
    """
    try:
        df = flatten_lists(df)
        df.to_sql(table_name, con=engine, if_exists="append", index=False)
        print(f"Saved {len(df)} rows to '{table_name}'")
    except Exception as e:
        print(f"Error saving to '{table_name}': {e}")
        raise


def query_db(sql: str) -> pd.DataFrame:
    """Execute a raw SQL query and return the results as a DataFrame.

    Args:
        sql: SQL string to execute.

    Returns:
        DataFrame containing query results.
    """
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


def test_connection():
    """Verify the database connection by running SELECT 1.

    Prints a success or failure message to stdout.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connection successful.")
    except Exception as e:
        print(f"Database connection failed: {e}")
