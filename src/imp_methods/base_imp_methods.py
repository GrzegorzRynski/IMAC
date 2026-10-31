import pandas as pd
import numpy as np
from typing import List, Tuple, Optional

def impute_mean(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Impute missing values in numeric columns using column means.
    """

    df_imputed = df.copy()

    mask = pd.DataFrame(False, index=df.index, columns=df.columns)

    if columns is None:
        return df_imputed, mask, {}

    vals = {}

    for col in columns:
        mean_value = df_imputed[col].mean()

        missing_mask = df_imputed[col].isna()

        df_imputed.loc[missing_mask, col] = mean_value

        vals[col] = round(mean_value, 2)

        mask.loc[missing_mask, col] = True

    return df_imputed, mask, vals

def impute_median(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Impute missing values in numeric columns using column medians.
    """

    df_imputed = df.copy()

    mask = pd.DataFrame(False, index=df.index, columns=df.columns)

    if columns is None:
        return df_imputed, mask, {}

    vals = {}

    for col in columns:
        median_value = df_imputed[col].median()

        missing_mask = df_imputed[col].isna()

        df_imputed.loc[missing_mask, col] = median_value

        vals[col] = round(median_value, 2)

        mask.loc[missing_mask, col] = True

    return df_imputed, mask, vals

def impute_mode(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Impute missing values in categorical columns using the most frequent value (mode).
    """

    df_imputed = df.copy()

    mask = pd.DataFrame(False, index=df.index, columns=df.columns)

    if columns is None:
        return df_imputed, mask, {}

    vals = {}

    for col in columns:
        mode_series = df_imputed[col].mode(dropna=True)

        if len(mode_series) > 0:
            mode_value = mode_series.iloc[0]
        else:
            mode_value = pd.NA

        missing_mask = df_imputed[col].isna()

        df_imputed.loc[missing_mask, col] = mode_value

        if not  pd.api.types.is_numeric_dtype(mode_value):
            vals[col] = mode_value if len(mode_value) < 10 else mode_value[:15] + "..."
        else:
            vals[col] = round(mode_value, 2)

        mask.loc[missing_mask, col] = True

    return df_imputed, mask, vals
