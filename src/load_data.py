import pandas as pd
from pathlib import Path

def load_csv(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Plik nie istnieje: {p}")
    df = pd.read_csv(p)
    return df

def describe_df(df: pd.DataFrame):
    print("\n--- Podstawowe informacje ---")
    print(df.info())

    print("\n--- Statystyki numeryczne ---")
    print(df.describe())

    print("\n--- Liczba braków danych ---")
    print(df.isnull().sum())