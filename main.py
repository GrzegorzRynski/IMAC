
import pandas as pd
from pathlib import Path

from evaluation.evaluation import evaluate_numeric_imputation, evaluate_categorical_imputation, \
    confusion_matrix_imputation
from imp_methods.base_imp_methods import impute_mean, impute_mode
from src.load_data import load_data_file
from src.init_analytics.init_analytics import *
from src.miss_sims.missingness import *
import matplotlib.pyplot as plt

DATA_DIR = Path("data")

def main():
    return

if __name__ == "__main__":
    main()