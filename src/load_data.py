import pandas as pd
from pathlib import Path

def load_data_file(path: str) -> pd.DataFrame:
    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(f"File doesn't exist: {p}")

    if not p.is_file():
        raise ValueError(f"Path is not a file: {p}")

    try:
        df = pd.read_csv(p, sep=None, engine="python")
    except pd.errors.EmptyDataError as e:
        raise ValueError(f"CSV file is empty: {p}") from e
    except pd.errors.ParserError as e:
        raise ValueError(f"Invalid CSV format: {p}") from e
    except UnicodeDecodeError as e:
        raise ValueError(f"Invalid encoding: {p}") from e

    if df.empty:
        raise ValueError(f"CSV contains no data: {p}")

    return df