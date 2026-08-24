import pandas as pd
import numpy as np
from typing import List, Tuple, Optional, Dict

def _sigmoid(x: np.ndarray) -> np.ndarray:
    """
    Simple sigmoid function: 1 / (1 + exp(-x)).
    """
    return 1.0 / (1.0 + np.exp(-x))

def generate_mcar(
    df: pd.DataFrame,
    rate: float,
    columns: Optional[List[str]] = None,
    random_state: Optional[int] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate MCAR (Missing Completely At Random) missingness in the given DataFrame.
    """

    df_missing = df.copy()

    rng = np.random.default_rng(random_state)

    if columns is None:
        columns = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    mask = pd.DataFrame(False, index=df.index, columns=df.columns)

    for col in columns:
        n = len(df_missing)

        probs = rng.random(n)

        col_mask = probs < rate

        df_missing.loc[col_mask, col] = np.nan
        mask.loc[col_mask, col] = True

    return df_missing, mask

def generate_mar(
    df: pd.DataFrame,
    target: str,
    predictor: str,
    base_rate: float = 0.1,
    strength: float = 0.5,
    random_state: Optional[int] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate MAR (Missing At Random) missingness in the target column.
    Missingness in `target` depends on values in `predictor`.
    """

    df_missing = df.copy()

    df_missing[predictor] = pd.to_numeric(df_missing[predictor], errors="coerce")

    rng = np.random.default_rng(random_state)

    if target not in df_missing.columns:
        raise ValueError(f"Target column '{target}' not found in DataFrame.")
    if predictor not in df_missing.columns:
        raise ValueError(f"Predictor column '{predictor}' not found in DataFrame.")

    x = df_missing[predictor].to_numpy()

    x_mean = np.nanmean(x)
    x_std = np.nanstd(x) if np.nanstd(x) > 0 else 1.0
    x_stdized = (x - x_mean) / x_std

    logits = base_rate + strength * x_stdized

    probs = _sigmoid(logits)

    n = len(df_missing)
    u = rng.random(n)

    col_mask = u < probs

    mask = pd.DataFrame(False, index=df.index, columns=df.columns)

    df_missing.loc[col_mask, target] = np.nan
    mask.loc[col_mask, target] = True

    return df_missing, mask

def generate_nmar(
    df: pd.DataFrame,
    target: str,
    base_rate: float = 0.1,
    strength: float = 0.5,
    random_state: Optional[int] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate NMAR (Missing Not At Random) missingness in the target column.

    Missingness depends on the values of the target column itself.

    """

    df_missing = df.copy()

    df_missing[target] = pd.to_numeric(df_missing[target], errors="coerce")

    rng = np.random.default_rng(random_state)

    if target not in df_missing.columns:
        raise ValueError(f"Target column '{target}' not found in DataFrame.")

    x = df_missing[target].to_numpy()

    x_mean = np.nanmean(x)
    x_std = np.nanstd(x) if np.nanstd(x) > 0 else 1.0
    x_stdized = (x - x_mean) / x_std

    logits = base_rate + strength * x_stdized

    probs = _sigmoid(logits)

    n = len(df_missing)
    u = rng.random(n)

    col_mask = u < probs

    mask = pd.DataFrame(False, index=df.index, columns=df.columns)

    df_missing.loc[col_mask, target] = np.nan
    mask.loc[col_mask, target] = True

    return df_missing, mask

def generate_mar_categorical(
    df: pd.DataFrame,
    target: str,
    predictor: str,
    predictor_probs: Dict[str, float],
    random_state: Optional[int] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate MAR missingness for a target column,
    where missingness depends on the categories of a predictor column.
    """

    df_missing = df.copy()

    rng = np.random.default_rng(random_state)

    if target not in df_missing.columns:
        raise ValueError(f"Target column '{target}' not found.")
    if predictor not in df_missing.columns:
        raise ValueError(f"Predictor column '{predictor}' not found.")

    mask = pd.DataFrame(False, index=df.index, columns=df.columns)

    for idx, pred_value in df_missing[predictor].items():
        prob = predictor_probs.get(pred_value, 0.0)

        u = rng.random()

        if u < prob:
            df_missing.at[idx, target] = np.nan
            mask.at[idx, target] = True

    return df_missing, mask

def generate_nmar_categorical(
    df: pd.DataFrame,
    target: str,
    category_probs: Dict[str, float],
    random_state: Optional[int] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate NMAR missingness for a categorical column.

    Missingness probability depends on the category itself.
    """

    df_missing = df.copy()

    rng = np.random.default_rng(random_state)

    if target not in df_missing.columns:
        raise ValueError(f"Target column '{target}' not found in DataFrame.")

    mask = pd.DataFrame(False, index=df.index, columns=df.columns)

    for idx, value in df_missing[target].items():
        prob = category_probs.get(value, 0.0)

        u = rng.random()

        if u < prob:
            df_missing.at[idx, target] = np.nan
            mask.at[idx, target] = True

    return df_missing, mask

def apply_missingness_pipeline(
    df: pd.DataFrame,
    mcar_rate: float = 0.0,
    mar_numeric: Optional[Dict[str, Dict]] = None,
    mar_categorical: Optional[Dict[str, Dict]] = None,
    nmar_numeric: Optional[Dict[str, Dict]] = None,
    nmar_categorical: Optional[Dict[str, Dict]] = None,
    random_state: Optional[int] = None,
    mode: str = "sequential"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Apply multiple missingness mechanisms (MCAR, MAR, NMAR) to a dataset.
    """

    if mode not in ("sequential", "independent"):
        raise ValueError("mode must be 'sequential' or 'independent'")

    base_rng = np.random.default_rng(random_state)

    df_original = df.copy()
    df_current = df.copy()

    final_mask = pd.DataFrame(False, index=df.index, columns=df.columns)

    def next_seed():
        return int(base_rng.integers(0, 2 ** 31 - 1))

    def run_method(func, *args, **kwargs):
        nonlocal final_mask
        seed = next_seed()
        kwargs["random_state"] = seed
        if mode == "sequential":
            nonlocal df_current
            df_current, mask = func(df_current, *args, **kwargs)
            final_mask |= mask
        elif mode == "independent":
            df_tmp, mask = func(df_original, *args, **kwargs)
            final_mask |= mask

    if mcar_rate > 0:
        run_method(generate_mcar, rate=mcar_rate)

    if mar_numeric:
        for target, params in mar_numeric.items():
            run_method(
                generate_mar,
                target=target,
                predictor=params["predictor"],
                base_rate=params.get("base_rate", 0.1),
                strength=params.get("strength", 0.5)
            )

    if mar_categorical:
        for target, params in mar_categorical.items():
            run_method(
                generate_mar_categorical,
                target=target,
                predictor=params["predictor"],
                predictor_probs=params["predictor_probs"]
            )

    if nmar_numeric:
        for target, params in nmar_numeric.items():
            run_method(
                generate_nmar,
                target=target,
                base_rate=params.get("base_rate", 0.1),
                strength=params.get("strength", 0.5)
            )

    if nmar_categorical:
        for target, params in nmar_categorical.items():
            run_method(
                generate_nmar_categorical,
                target=target,
                category_probs=params["category_probs"]
            )

    if mode == "independent":
        df_final = df_original.copy()
        df_final[final_mask] = np.nan
    elif mode == "sequential":
        df_final = df_current

    return df_final, final_mask