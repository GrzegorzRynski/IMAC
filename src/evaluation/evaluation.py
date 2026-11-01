import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Any, Callable, Tuple
from sklearn.metrics import f1_score, accuracy_score, confusion_matrix

def evaluate_numeric_imputation(
    df_original: pd.DataFrame,
    df_imputed: pd.DataFrame,
    mask_missing: pd.DataFrame,
    columns: Optional[List[str]] = None
) -> Dict[str, Dict[str, float| None]]:
    """
    Evaluate numeric imputation quality using MAE and RMSE.
    """

    if columns is None:
        columns = [c for c in df_original.columns
                   if pd.api.types.is_numeric_dtype(df_original[c])]

    metrics: Dict[str, Dict[str, float| None]] = {}

    for col in columns:
        missing_mask = mask_missing[col]

        y_true = df_original.loc[missing_mask, col].to_numpy()
        y_pred = df_imputed.loc[missing_mask, col].to_numpy()

        valid_mask = pd.notna(y_pred)

        y_true = y_true[valid_mask]
        y_pred = y_pred[valid_mask]

        if len(y_true) == 0:
            continue

        mae = np.mean(np.abs(y_true - y_pred))

        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))

        true_max = df_original[col].max()
        true_min = df_original[col].min()

        nrmse = rmse / (true_max - true_min) if true_max - true_min != 0 else None

        metrics[col] = {
            "MAE": float(mae),
            "RMSE": float(rmse),
            "NRMSE": float(nrmse) if nrmse is not None else None
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

        valid_mask = pd.notna(y_pred)

        y_true = y_true[valid_mask]
        y_pred = y_pred[valid_mask]

        if len(y_true) == 0:
            continue

        acc = accuracy_score(y_true, y_pred)

        f1 = f1_score(
            y_true,
            y_pred,
            average="macro",
            zero_division=0
        )

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

        valid_mask = pd.notna(y_pred)

        y_true = y_true[valid_mask]
        y_pred = y_pred[valid_mask]

        if len(y_true) == 0:
            continue

        labels = pd.unique(
            np.concatenate([
                df_original[col].dropna().to_numpy(),
                y_pred
            ])
        )
        cm = confusion_matrix(y_true, y_pred, labels=labels)

        cm_df = pd.DataFrame(cm, index=labels, columns=labels)

        matrices[col] = cm_df

    return matrices

def calculate_coverage(
    df_imputed: pd.DataFrame,
    mask_missing: pd.DataFrame,
    columns: List[str]
) -> Dict[str, float| None]:

    total_missing = mask_missing[columns].to_numpy().sum()

    if total_missing == 0:
        return {
            "coverage": None,
            "imputed": 0,
            "total": 0
        }

    imputed_mask = (
        mask_missing[columns]
        & df_imputed[columns].notna()
    )

    imputed_count = imputed_mask.to_numpy().sum()

    return {
        "coverage": float(imputed_count / total_missing),
        "imputed": int(imputed_count),
        "total": int(total_missing)
    }

def validate_evaluation_data(
    df_original: pd.DataFrame,
    df_imputed: pd.DataFrame,
    mask_missing: pd.DataFrame
) -> None:

    if not df_original.index.equals(df_imputed.index):
        raise ValueError("Original and imputed indexes do not match.")

    if not df_original.columns.equals(df_imputed.columns):
        raise ValueError("Original and imputed columns do not match.")

    if not df_original.index.equals(mask_missing.index):
        raise ValueError("Original and missing mask indexes do not match.")

    if not df_original.columns.equals(mask_missing.columns):
        raise ValueError("Original and missing mask columns do not match.")

def evaluate_imputation_method(
    df_original: pd.DataFrame,
    df_imputed: pd.DataFrame,
    mask_missing: pd.DataFrame,
    numeric_columns: List[str],
    categorical_columns: List[str],
    determine_confusion_matrices: bool = True
) -> Dict[str, Any]:
    """
    Evaluate a single imputation method across numeric and categorical columns.
    """

    validate_evaluation_data(
        df_original,
        df_imputed,
        mask_missing
    )

    all_columns = numeric_columns + categorical_columns

    if not set(all_columns).issubset(df_original.columns):
        raise ValueError("Some evaluation columns do not exist.")

    if len(all_columns) != len(set(all_columns)):
        raise ValueError("Evaluation columns contain duplicates.")

    results = { "coverage": {
        "numeric": calculate_coverage(
            df_imputed, mask_missing, numeric_columns
        ),
        "categorical": calculate_coverage(
            df_imputed, mask_missing, categorical_columns
        ),
        "overall": calculate_coverage(
            df_imputed,
            mask_missing,
            numeric_columns + categorical_columns
        )
    }}

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

    if determine_confusion_matrices:
        confusion_matrices = confusion_matrix_imputation(
            df_original=df_original,
            df_imputed=df_imputed,
            mask_missing=mask_missing,
            columns=categorical_columns
        )
    else:
        confusion_matrices = None

    results["numeric"] = numeric_metrics
    results["categorical"] = categorical_metrics
    results["confusion_matrices"] = confusion_matrices

    return results

def imputation_methods_report(
    df_reference: pd.DataFrame,
    df_missing: pd.DataFrame,
    imputed_datasets: Dict[str, pd.DataFrame],
    numeric_columns: List[str],
    categorical_columns: List[str],
    determine_confusion_matrices: bool = True,
) -> Dict[str, Any]:

    mask_missing = (
        df_missing.isna()
        & df_reference.notna()
    )

    results = {}

    for result_name, df_imputed in imputed_datasets.items():
        results[result_name] = evaluate_imputation_method(
            df_original=df_reference,
            df_imputed=df_imputed,
            mask_missing=mask_missing,
            numeric_columns=numeric_columns,
            categorical_columns=categorical_columns,
            determine_confusion_matrices=determine_confusion_matrices
        )

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
                "RMSE": metrics["RMSE"],
                "NRMSE": metrics["NRMSE"]
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