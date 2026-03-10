from sqlalchemy import create_engine, text
import pandas as pd

engine = create_engine("sqlite:///data/cfb.db")

def flatten_lists(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, (list, dict))).any():
            df[col] = df[col].apply(lambda x: str(x) if isinstance(x, (list, dict)) else x)
    return df

def save_to_db(df: pd.DataFrame, table_name: str):
    df = flatten_lists(df)
    df.to_sql(table_name, con=engine, if_exists="append", index=False)
    print(f"Saved {len(df)} rows to '{table_name}'")

def query_db(sql: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)