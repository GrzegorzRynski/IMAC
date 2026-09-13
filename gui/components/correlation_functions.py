import numpy as np
import pandas as pd
import scipy.stats as ss

def cramers_v(x, y):
    confusion_matrix = pd.crosstab(x, y)
    if confusion_matrix.size == 0:
        return np.nan
    chi2 = ss.chi2_contingency(confusion_matrix)[0]
    n = confusion_matrix.sum().sum()
    r, k = confusion_matrix.shape
    return np.sqrt(chi2 / (n * (min(r, k) - 1)))

def correlation_ratio(categories, values):
    categories = np.array(categories)
    values = np.array(values)

    if len(values) == 0:
        return np.nan

    cat_values = [values[categories == cat] for cat in np.unique(categories)]
    means = [np.mean(v) for v in cat_values]
    overall_mean = np.mean(values)

    numerator = sum([len(v) * (m - overall_mean)**2 for v, m in zip(cat_values, means)])
    denominator = sum((values - overall_mean)**2)

    return np.sqrt(numerator / denominator) if denominator != 0 else np.nan