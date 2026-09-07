import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Any, Callable, Tuple
from sklearn.metrics import f1_score, accuracy_score, confusion_matrix

def evaluate_numeric_imputation(
    df_original: pd.DataFrame,
    df_imputed: pd.DataFrame,
    mask_missing: pd.DataFrame,
    columns: Optional[List[str]] = None
) -> Dict[str, Dict[str, float]]:
    """
    Evaluate numeric imputation quality using MAE and RMSE.
    """

    if columns is None:
        columns = [c for c in df_original.columns
                   if pd.api.types.is_numeric_dtype(df_original[c])]

    metrics: Dict[str, Dict[str, float]] = {}

    for col in columns:
        missing_mask = mask_missing[col]

        y_true = df_original.loc[missing_mask, col].to_numpy()
        y_pred = df_imputed.loc[missing_mask, col].to_numpy()

        if len(y_true) == 0:
            continue

        mae = np.mean(np.abs(y_true - y_pred))

        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))

        metrics[col] = {
            "MAE": float(mae),
            "RMSE": float(rmse)
        }

    return metrics

def evaluate_categorical_imputation(
    df_original: pd.DataFrame,
    df_imputed: pd.DataFrame,
    mask_missing: pd.DataFrame,
    columns: Optional[List[str]] = None
) -> Dict[str, Dict[str, float]]:
    """
    Evaluate categorical imputation using Accuracy and Macro F1-score.
    """

    if columns is None:
        columns = [c for c in df_original.columns
                   if not pd.api.types.is_numeric_dtype(df_original[c])]

    metrics: Dict[str, Dict[str, float]] = {}

    for col in columns:
        missing_mask = mask_missing[col]

        y_true = df_original.loc[missing_mask, col].to_numpy()
        y_pred = df_imputed.loc[missing_mask, col].to_numpy()

        if len(y_true) == 0:
            continue

        acc = accuracy_score(y_true, y_pred)

        f1 = f1_score(y_true, y_pred, average="macro")

        metrics[col] = {
            "Accuracy": float(acc),
            "MacroF1": float(f1)
        }

    return metrics

def confusion_matrix_imputation(
    df_original: pd.DataFrame,
    df_imputed: pd.DataFrame,
    mask_missing: pd.DataFrame,
    columns: Optional[List[str]] = None
) -> Dict[str, pd.DataFrame]:
    """
    Compute confusion matrices for categorical imputation.
    """

    if columns is None:
        columns = [c for c in df_original.columns
                   if not pd.api.types.is_numeric_dtype(df_original[c])]

    matrices: Dict[str, pd.DataFrame] = {}

    for col in columns:
        missing_mask = mask_missing[col]

        y_true = df_original.loc[missing_mask, col].to_numpy()
        y_pred = df_imputed.loc[missing_mask, col].to_numpy()

        if len(y_true) == 0:
            continue

        labels = np.unique(np.concatenate([y_true, y_pred]))
        cm = confusion_matrix(y_true, y_pred, labels=labels)

        cm_df = pd.DataFrame(cm, index=labels, columns=labels)

        matrices[col] = cm_df

    return matrices

def evaluate_imputation_method(
    df_original: pd.DataFrame,
    df_imputed: pd.DataFrame,
    mask_missing: pd.DataFrame,
    numeric_columns: List[str],
    categorical_columns: List[str]
) -> Dict[str, Any]:
    """
    Evaluate a single imputation method across numeric and categorical columns.
    """
    results = {}

    numeric_metrics = evaluate_numeric_imputation(
        df_original=df_original,
        df_imputed=df_imputed,
        mask_missing=mask_missing,
        columns=numeric_columns
    )

    categorical_metrics = evaluate_categorical_imputation(
        df_original=df_original,
        df_imputed=df_imputed,
        mask_missing=mask_missing,
        columns=categorical_columns
    )

    confusion_matrices = confusion_matrix_imputation(
        df_original=df_original,
        df_imputed=df_imputed,
        mask_missing=mask_missing,
        columns=categorical_columns
    )

    results["numeric"] = numeric_metrics
    results["categorical"] = categorical_metrics
    results["confusion_matrices"] = confusion_matrices

    return results

def imputation_methods_report(
    df_original: pd.DataFrame,
    df_missing: pd.DataFrame,
    mask_missing: pd.DataFrame,
    methods: Dict[str, Callable[[pd.DataFrame], Tuple[pd.DataFrame, pd.DataFrame]]],
    numeric_columns: List[str],
    categorical_columns: List[str]
) -> Dict[str, Any]:
    """
    Compare multiple imputation methods.
    """
    results = {}

    for method_name, imputer in methods.items():

        df_imputed, _ = imputer(df_missing)

        evaluation = evaluate_imputation_method(
            df_original=df_original,
            df_imputed=df_imputed,
            mask_missing=mask_missing,
            numeric_columns=numeric_columns,
            categorical_columns=categorical_columns
        )

        results[method_name] = evaluation

    return results

def summarize_comparison_results(
    comparison_results: Dict[str, Any]
) -> Dict[str, pd.DataFrame]:
    """
    Summarize comparison results into numeric and categorical tables.
    """

    numeric_rows = []

    for method_name, report in comparison_results.items():
        numeric_metrics = report["numeric"]

        for col, metrics in numeric_metrics.items():
            numeric_rows.append({
                "method": method_name,
                "column": col,
                "MAE": metrics["MAE"],
                "RMSE": metrics["RMSE"]
            })

    numeric_df = pd.DataFrame(numeric_rows)

    categorical_rows = []

    for method_name, report in comparison_results.items():
        categorical_metrics = report["categorical"]

        for col, metrics in categorical_metrics.items():
            categorical_rows.append({
                "method": method_name,
                "column": col,
                "Accuracy": metrics["Accuracy"],
                "MacroF1": metrics["MacroF1"]
            })

    categorical_df = pd.DataFrame(categorical_rows)

    return {
        "numeric": numeric_df,
        "categorical": categorical_df
    }