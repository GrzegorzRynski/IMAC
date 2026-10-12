import numpy as np
import pandas as pd
import scipy.stats as ss

def cramers_v(x, y):
    valid = pd.notna(x) & pd.notna(y)

    x = pd.Series(x)[valid]
    y = pd.Series(y)[valid]

    if len(x) == 0:
        return np.nan

    confusion_matrix = pd.crosstab(x, y)

    if confusion_matrix.empty:
        return np.nan

    chi2 = ss.chi2_contingency(confusion_matrix)[0]

    n = confusion_matrix.sum().sum()

    if n == 0:
        return np.nan

    r, k = confusion_matrix.shape

    if min(r, k) <= 1:
        return np.nan

    return np.sqrt(chi2 / (n * (min(r, k) - 1)))

def correlation_ratio(categories, values):
    valid = pd.notna(categories) & pd.notna(values)

    categories = np.array(categories[valid])
    values = np.array(values[valid])

    if len(values) == 0:
        return np.nan

    unique_categories = np.unique(categories)

    if len(unique_categories) <= 1:
        return np.nan

    cat_values = [
        values[categories == cat]
        for cat in unique_categories
    ]

    means = [np.mean(v) for v in cat_values]
    overall_mean = np.mean(values)

    numerator = sum(
        len(v) * (m - overall_mean) ** 2
        for v, m in zip(cat_values, means)
    )

    denominator = np.sum(
        (values - overall_mean) ** 2
    )

    if denominator == 0:
        return np.nan

    return np.sqrt(numerator / denominator)