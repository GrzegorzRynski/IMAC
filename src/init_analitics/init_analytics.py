import pandas as pd
import numpy as np
from typing import Dict, List

from pandas import DataFrame, Series


def infer_column_types(df: pd.DataFrame, cat_threshold: int = 20) -> Dict[str, List[str]]:
    """
    Determine column types: numeric, categorical, and text-like.
    Categorical columns are detected by low cardinality (<= cat_threshold).
    """
    numeric = []
    categorical = []
    text = []

    for col in df.columns:
        ser = df[col]  # column as pandas Series

        # Check if column is numeric
        if pd.api.types.is_numeric_dtype(ser):
            numeric.append(col)
        else:
            # Count unique non-null values to decide categorical vs text
            nunique = ser.nunique(dropna=True)
            if nunique <= cat_threshold:
                categorical.append(col)
            else:
                text.append(col)

    return {"numeric": numeric, "categorical": categorical, "text": text}


def missing_summary(df: pd.DataFrame, unusual_tokens: List[str] | None = None) -> pd.DataFrame:
    """
    Summarize missing values and detect unusual tokens used as missing markers.
    """
    if unusual_tokens is None:
        unusual_tokens = ["?", "-9", "NA", "N/A", "nan"]

    total = len(df)  # number of rows
    miss_count = df.isnull().sum()  # count of NaN per column
    miss_pct = (miss_count / total) * 100  # percentage of missing values

    unusual = {}  # store unusual token counts per column

    for col in df.columns:
        ser = df[col].astype(str)  # convert to string for token comparison
        count = 0

        # Count occurrences of unusual tokens
        for tok in unusual_tokens:
            count += ser.str.strip().eq(tok).sum()

        unusual[col] = count

    # Build summary DataFrame
    res = pd.DataFrame({
        "missing_count": miss_count,
        "missing_pct": miss_pct,
        "unusual_token_count": pd.Series(unusual)
    })

    return res.sort_values("missing_count", ascending=False)


def basic_stats(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Return descriptive statistics for numeric and categorical columns.
    """
    types = infer_column_types(df)

    # Numeric stats (mean, std, min, quartiles, max)
    numeric = df[types["numeric"]].describe().transpose() if types["numeric"] else pd.DataFrame()

    # Categorical stats (count, unique, top, freq)
    categorical = df[types["categorical"]].describe().transpose() if types["categorical"] else pd.DataFrame()

    return {"numeric": numeric, "categorical": categorical}


def value_counts_sample(df: pd.DataFrame, n: int = 5) -> Dict[str, pd.Series]:
    """
    Return top-n most frequent values for each categorical column.
    """
    types = infer_column_types(df)
    res = {}

    for col in types["categorical"]:
        res[col] = df[col].value_counts(dropna=False).head(n)

    return res


def correlation_matrix(df: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
    """
    Compute correlation matrix for numeric columns.
    """
    types = infer_column_types(df)

    if not types["numeric"]:
        return pd.DataFrame()

    return df[types["numeric"]].corr(method=method)


def preview(df: pd.DataFrame, n: int = 5) -> dict[str, DataFrame | Series]:
    """
    Return head, tail, and dtypes for quick dataset preview.
    """
    return {
        "head": df.head(n),
        "tail": df.tail(n),
        "dtypes": df.dtypes
    }


def report(df: pd.DataFrame) -> Dict[str, object]:
    """
    Aggregate all analysis results into a single dictionary.
    """
    types = infer_column_types(df)
    missing = missing_summary(df)
    stats = basic_stats(df)
    values = value_counts_sample(df)
    corr = correlation_matrix(df)
    prev = preview(df)

    return {
        "preview": prev,
        "types": types,
        "missing": missing,
        "basic_stats": stats,
        "value_counts": values,
        "correlation": corr
    }
