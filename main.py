
import pandas as pd
from pathlib import Path
from src.load_data import load_csv, describe_df
from src.init_analitics.init_analytics import *
from src.miss_sims.missingness import *
import matplotlib.pyplot as plt

DATA_DIR = Path("data")

def main():
    csv_path = DATA_DIR / "processed.cleveland.data"

    if not csv_path.exists():
        print(f"Brak pliku {csv_path.name} w katalogu data.")
        return

    df = load_csv(csv_path)
    #print("Pierwsze wiersze danych:")
    #print(df.head())

    #describe_df(df)

    # df['age'].hist(bins=20)
    # plt.title("Rozkład wieku")
    # plt.xlabel("Wiek")
    # plt.ylabel("Liczba pacjentów")
    # plt.show()

    column_types = infer_column_types(df)
    missing_summ = missing_summary(df)
    basic_stat = basic_stats(df)
    corr_matrix = correlation_matrix(df)
    prev = preview(df)
    rep = report(df)

    print("--------------------------")
    #print(column_types)
    #print(missing_summ)
    #print(basic_stat)
    #print(corr_matrix)
    #print(rep)

    # mcar_df, mask = generate_mcar(df, 0.1, df.columns)
    # mcar_rep = report(mcar_df)
    # print(mcar_rep)

    df_mar, mask_mar = generate_mar(
        df,
        target="chol",
        predictor="age",
        base_rate=0.1,
        strength=0.8,
        random_state=42
    )

    # mar_rep = report(df_mar)
    # print(mar_rep)

    df_nmar, mask_nmar = generate_nmar(
        df,
        target="thal",
        base_rate=0.05,
        strength=1.2,
        random_state=42
    )

    nmar_rep = report(df_nmar)

    df_missing, mask = apply_missingness_pipeline(
        df,
        mcar_rate=0.05,

        mar_numeric={
            "chol": {"predictor": "age", "base_rate": 0.1, "strength": 0.8}
        },

        nmar_numeric={
            "thal": {"base_rate": 0.05, "strength": 1.2}
        },

        random_state=42
    )

    df_missing_rep = report(df_missing)
    print(df_missing_rep)

if __name__ == "__main__":
    main()