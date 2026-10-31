import os
import tkinter
from json import JSONDecodeError
from pathlib import Path

import CTkMessagebox
import numpy as np
import pandas as pd
import json

from history_manager import HistoryManager
from imp_methods.base_imp_methods import impute_mean, impute_mode, impute_median
from init_analitics.init_analytics import report, missing_summary
from load_data import load_data_file
from miss_sims.missingness import (
    apply_missingness_pipeline as run_miss_pipeline,
)


class ImputationManager:

    def __init__(self):

        self.remembered_locations = []
        self.current_df = None
        self.original_df = None
        self.current_name = ""
        self.current_path = ""
        self.df_history = HistoryManager(self)
        self.current_index = 0

        self.on_change_callbacks = []
        self.on_save_callbacks = []

        self.data_file = "app_data.json"
        self.data_folder = "data"
        self.data = None

        self.settings={"missingness" : {}}

        self.imputation_method_registry = {
            "Mean": self.apply_mean_imputation_action,
            "Median": self.apply_median_imputation_action,
            "Mode": self.apply_mode_imputation_action,
        }

        self.action_registry = {
            "load_dataset": self.load_dataset_action,
            "mark_unusual_as_missing": self.mark_unusual_as_missing_action,
            "delete_unusual_rows": self.delete_unusual_rows_action,
            "apply_missingness_pipeline": self.apply_missingness_pipeline_action,
            "apply_mean_imputation": self.apply_mean_imputation_action,
            "apply_median_imputation": self.apply_median_imputation_action,
            "apply_mode_imputation": self.apply_mode_imputation_action,
        }

    def register_update_callback(self, callback):
        if callback not in self.on_change_callbacks:
            self.on_change_callbacks.append(callback)

    def notify_change(self):
        for cb in self.on_change_callbacks:
            cb()

    def register_save_callback(self, callback):
        if callback not in self.on_save_callbacks:
            self.on_save_callbacks.append(callback)

    def notify_save(self):
        for cb in self.on_save_callbacks:
            cb()

    def load_app_data(self):

        main_folder = Path(__file__).resolve().parent.parent
        data_file = main_folder / self.data_file

        if not os.path.exists(data_file):
            return

        try:
            with open(data_file, "r") as f:
                data = json.load(f)
        except JSONDecodeError:
            CTkMessagebox.CTkMessagebox(
                title="Error",
                message="An error has occured while reading app data!",
                icon="cancel"
            )
            data = None

        self.data = data

        self.load_remembered_locations()

        self.init_settings()

        if data is not None:
            settings = self.data.get("settings", {}) or {}
            current_path = self.data.get("last_used_file", "") or ""
        else:
            settings = {}
            current_path = ""

        self.load_settings(settings)

        if not current_path:
            return

        try:
            df = load_data_file(current_path)
        except FileNotFoundError:

            CTkMessagebox.CTkMessagebox(
                title="Error",
                message="Could not load last used dataset.\nFile was moved or deleted.",
                icon="cancel"
            )

            self.register_update_callback(self.save_app_data)
            self.save_app_data()

            return

        except ValueError:

            CTkMessagebox.CTkMessagebox(
                title="Error",
                message="Could not load last used dataset.\nFile is not in a correct format or is unreadable.",
                icon="cancel"
            )

            self.register_update_callback(self.save_app_data)
            self.save_app_data()

            return

        self.load_df(df, current_path, remembered=True)

        history_data = data.get("history")

        try:
            self.df_history.load_history(history_data)
            self.load_dataset_state(
                self.df_history.current_branch,
                self.df_history.current_action_index
            )
        except (ValueError, KeyError, TypeError):
            self.df_history.clear_history()
            self.load_dataset_action()
            self.notify_change()

        self.register_update_callback(self.save_app_data)

    def init_settings(self):
        # --- MISSINGNESS ---
        self.settings.setdefault("missingness", {})

        missingness = self.settings["missingness"]
        missingness.setdefault("method_settings", {})
        missingness.setdefault("rng_seeds", {})

        method_settings = missingness["method_settings"]
        method_settings.setdefault("selected_mechanism", None)
        method_settings.setdefault("mcar_missingness_rate", None)
        method_settings.setdefault("active_methods", None)
        method_settings.setdefault("mar_predictor", None)
        method_settings.setdefault("base_rates", None)
        method_settings.setdefault("strengths", None)
        method_settings.setdefault("method_columns", None)
        method_settings.setdefault("categorical_column_rates", None)
        method_settings.setdefault("method_order", None)

        rng_seeds = missingness["rng_seeds"]
        rng_seeds.setdefault("seeds", None)
        rng_seeds.setdefault("current_rng_seed", None)
        rng_seeds.setdefault("always_random_seed", None)

        missingness.setdefault("pipeline_mode", None)

        # --- IMPUTATION ---
        self.settings.setdefault("imputation", {})

        imputation = self.settings["imputation"]
        imputation.setdefault("selected_method", None)
        imputation.setdefault("selected_columns", None)
        imputation.setdefault("method_parameters", None)

        # --- EVALUATION ---
        self.settings.setdefault("evaluation", {})

        evaluation = self.settings["evaluation"]

        evaluation.setdefault("auto_selection", None)

        evaluation.setdefault("single", {})
        evaluation.setdefault("comparison", {})

        single_settings = evaluation["single"]
        single_settings.setdefault("branch_id", None)
        single_settings.setdefault("reference_id", None)
        single_settings.setdefault("missing_id", None)
        single_settings.setdefault("result_id", None)

        comparison_settings = evaluation["comparison"]
        comparison_settings.setdefault("branch_id", None)
        comparison_settings.setdefault("reference_id", None)
        comparison_settings.setdefault("missing_id", None)
        comparison_settings.setdefault("results", None)

    def load_settings(self, settings):
        # --- MISSINGNESS ---
        missingness = self.settings["missingness"]
        missingness_settings = settings.get("missingness") or {}

        method_settings = missingness_settings.get("method_settings", {}) or {}
        target_method_settings = missingness["method_settings"]

        target_method_settings["selected_mechanism"] = method_settings.get("selected_mechanism")
        target_method_settings["mcar_missingness_rate"] = method_settings.get("mcar_missingness_rate")
        target_method_settings["active_methods"] = method_settings.get("active_methods")
        target_method_settings["mar_predictor"] = method_settings.get("mar_predictor")
        target_method_settings["base_rates"] = method_settings.get("base_rates")
        target_method_settings["strengths"] = method_settings.get("strengths")
        target_method_settings["method_columns"] = method_settings.get("method_columns")
        target_method_settings["categorical_column_rates"] = method_settings.get("categorical_column_rates")
        target_method_settings["method_order"] = method_settings.get("method_order")

        rng_seeds = missingness_settings.get("rng_seeds", {}) or {}
        target_rng_seeds = missingness["rng_seeds"]

        target_rng_seeds["seeds"] = rng_seeds.get("seeds")
        target_rng_seeds["current_rng_seed"] = rng_seeds.get("current_rng_seed")
        target_rng_seeds["always_random_seed"] = rng_seeds.get("always_random_seed")

        missingness["pipeline_mode"] = missingness_settings.get("pipeline_mode", "Sequential")

        # --- IMPUTATION ---
        imputation = self.settings["imputation"]
        imputation_settings = settings.get("imputation") or {}

        imputation["selected_method"] = imputation_settings.get("selected_method")
        imputation["selected_columns"] = imputation_settings.get("selected_columns")
        imputation["method_parameters"] = imputation_settings.get("method_parameters")

        # --- EVALUATION ---
        evaluation = self.settings["evaluation"]
        evaluation_settings = settings.get("evaluation") or {}

        evaluation["auto_selection"] = evaluation_settings.get("auto_selection")

        single_settings = evaluation_settings.get("single", {}) or {}
        target_single_settings = evaluation["single"]

        target_single_settings["branch_id"] = single_settings.get("branch_id")
        target_single_settings["reference_id"] = single_settings.get("reference_id")
        target_single_settings["missing_id"] = single_settings.get("missing_id")
        target_single_settings["result_id"] = single_settings.get("result_id")

        comparison_settings = evaluation_settings.get("comparison") or {}
        target_comparison_settings = evaluation["comparison"]

        target_comparison_settings["branch_id"] = comparison_settings.get("branch_id")
        target_comparison_settings["reference_id"] = comparison_settings.get("reference_id")
        target_comparison_settings["missing_id"] = comparison_settings.get("missing_id")
        target_comparison_settings["results"] = comparison_settings.get("results")

    def load_remembered_locations(self) -> None:

        self.remembered_locations = []

        self.load_data_folder()

        if self.data is None:
            return

        remembered_locations = self.data.get("recent_files", [])

        for file in remembered_locations:
            if Path(file).is_file() and str(file) not in self.remembered_locations:
                self.remembered_locations.append(str(file))

    def save_app_data(self):

        main_folder = Path(__file__).resolve().parent.parent
        data_file = main_folder / self.data_file

        history_data = self.df_history.save_history()

        self.notify_save()

        data = {
            "recent_files": self.remembered_locations,
            "last_used_file": self.current_path,
            "history": history_data,
            "settings": self.settings
        }

        with open(data_file, "w") as f:
            json.dump(data, f, indent=4)

    def load_data_folder(self) -> None:
        """
        Searches application data folder for .csv and .data. files
        """
        main_folder = Path(__file__).resolve().parent.parent
        data_folder = main_folder / self.data_folder

        if not data_folder.exists():
            data_folder.mkdir(parents=True, exist_ok=True)
            return

        for file in data_folder.iterdir():
            if file.is_file() and file.suffix.lower() in ['.csv', '.data'] and str(file) not in self.remembered_locations:
                self.remembered_locations.append(str(file))

    def load_df(self, df, df_path, remembered = False):

        self.current_name = Path(df_path).name
        self.current_path = df_path
        self.current_df = df
        self.original_df = df
        if not remembered:
            self.df_history.clear_history()
            self.load_dataset_action()
            self.notify_change()

        if str(df_path) not in self.remembered_locations:
            self.remembered_locations.append(str(df_path))

    def mark_unusual_as_missing(self, report, unusual_tokens = None) -> None:
        if unusual_tokens is None:
            unusual_tokens = [
                "",
                " ",
                "NA",
                "N/A",
                "NULL",
                "null",
                "?",
                "-"
            ]

        unusual_report = report["missing"]

        unusual_token_count = unusual_report["unusual_token_count"]

        if unusual_token_count.sum() > 0:
            self.current_df = self.mark_unusual_as_missing_action(self.current_df, True, unusual_tokens=unusual_tokens, unusual_token_count=unusual_token_count)
            self.notify_change()

    def delete_unusual_rows(self, report, unusual_tokens = None) -> None:
        if unusual_tokens is None:
            unusual_tokens = [
                "",
                " ",
                "NA",
                "N/A",
                "NULL",
                "null",
                "?",
                "-"
            ]

        unusual_report = report["missing"]

        unusual_token_count = unusual_report["unusual_token_count"]

        if unusual_token_count.sum() > 0:
            self.current_df = self.delete_unusual_rows_action(self.current_df, True, unusual_tokens=unusual_tokens, unusual_token_count=unusual_token_count)
            self.notify_change()

    def apply_missingness_pipeline(
            self,
            active_methods,
            mcar_missingness_rate,
            method_columns,
            categorical_column_rates,
            method_order,
            mar_predictor,
            base_rates,
            strengths,
            rng_seed,
            always_random_seed,
            pipeline_mode
    ):
        df = self.current_df

        if df is None:
            return

        active = {
            method: value
            for method, value in active_methods.items()
        }

        ordered_methods = [
            method
            for method in method_order
            if active.get(method, False)
        ]

        if not ordered_methods:
            return

        mcar_columns = method_columns.get("MCAR", [])

        mar_numeric = {}
        mar_categorical = {}
        nmar_numeric = {}
        nmar_categorical = {}

        if active.get("MAR", False):
            predictor = mar_predictor

            predictor_is_numeric = pd.api.types.is_numeric_dtype(
                df[predictor]
            )

            for target in method_columns.get("MAR", []):
                if target == predictor:
                    continue

                if predictor_is_numeric:
                    mar_numeric[target] = {
                        "predictor": predictor,
                        "base_rate": base_rates["MAR"],
                        "strength": strengths["MAR"],
                    }
                else:
                    predictor_probs = categorical_column_rates.get(
                        "MAR", {}
                    ).get(predictor, {})

                    mar_categorical[target] = {
                        "predictor": predictor,
                        "predictor_probs": predictor_probs,
                    }

        if active.get("NMAR", False):
            for target in method_columns.get("NMAR", []):
                if pd.api.types.is_numeric_dtype(df[target]):
                    nmar_numeric[target] = {
                        "base_rate": base_rates["NMAR"],
                        "strength": strengths["NMAR"],
                    }
                else:
                    category_probs = categorical_column_rates.get(
                        "NMAR", {}
                    ).get(target, {})

                    nmar_categorical[target] = {
                        "category_probs": category_probs,
                    }

        if always_random_seed:
            rng_seed = int(
                np.random.default_rng().integers(0, 2 ** 32)
            )

        result_df = self.apply_missingness_pipeline_action(
            df=df,
            mcar_rate=mcar_missingness_rate,
            mcar_columns=mcar_columns,
            mar_numeric=mar_numeric,
            mar_categorical=mar_categorical,
            nmar_numeric=nmar_numeric,
            nmar_categorical=nmar_categorical,
            random_state=rng_seed,
            mode=(
                "independent"
                if pipeline_mode== "Independent"
                else "sequential"
            ),
            method_order=ordered_methods,
        )

        self.current_df = result_df
        self.notify_change()

    def apply_imputation(self, method, columns, parameters):
        df = self.current_df

        if df is None:
            return

        if method not in self.imputation_method_registry.keys():
            return

        if not all(col in df.columns for col in columns):
            return

        result_df = self.imputation_method_registry[method](df, columns=columns, **parameters)

        self.current_df = result_df
        self.notify_change()

    # ------------------------- HISTORY LOADING --------------------------------------

    def load_dataset_state(self, branch_index, branch_action_id):
        try:
            new_state = self.get_dataset_state(
                branch_index,
                branch_action_id
            )
        except ValueError:
            self.df_history.clear_history()
            self.load_dataset_action()
            self.notify_change()
            return
        except IndexError:
            if branch_action_id <= 0:
                self.df_history.clear_history()
                self.load_dataset_action()
                self.notify_change()
            else:
                self.load_dataset_state(branch_index, branch_action_id - 1)
            return

        self.current_df = new_state
        self.notify_change()

    def get_dataset_state(self, branch_index, branch_action_index):
        branch = self.df_history.get_history_branch(branch_index)

        if not 0 <= branch_action_index < len(branch):
            raise IndexError("Invalid history action index.")

        new_state = pd.DataFrame()

        for index, action in enumerate(branch):
            new_state = self.perform_action(
                new_state,
                action["action"],
                action["args"]
            )

            if index == branch_action_index:
                break

        return new_state

    def perform_action(self, current_df_state, action_name, action_args):
        func = self.action_registry[action_name]
        return func(current_df_state, False, **action_args)

    # ------------------------- DATAFRAME ACTIONS --------------------------------------

    def load_dataset_action(self, df = None, add_history_entry = True, **kwargs) -> pd.DataFrame:
        if add_history_entry:
            if len(self.current_name) > 24:
                name = self.current_name[:24]+"..."
            else:
                name = self.current_name
            self.df_history.add_action(
                action_id=0,
                action_name="load_dataset",
                args={"Dataframe" : name},
                name="Load Dataset",
                desc="Load dataset file"
            )
        return self.original_df.copy()

    def mark_unusual_as_missing_action(self, df: pd.DataFrame, add_history_entry: bool = True, **kwargs) -> pd.DataFrame:

        unusual_tokens = kwargs.get("unusual_tokens", None)
        unusual_token_count = kwargs.get("unusual_token_count", None)

        if unusual_token_count is not None:
            for col in df.columns:
                if unusual_token_count[col] == 0:
                    continue
                df[col] = df[col].astype(str).str.strip()

        df = df.replace(unusual_tokens, pd.NA)

        if add_history_entry:
            self.df_history.add_action(
                action_id=1,
                action_name="mark_unusual_as_missing",
                args={
                    "unusual_tokens": unusual_tokens,
                    "unusual_token_count": unusual_token_count
                },
                name="Mark Unusual Tokens As Missing",
                desc=f"{unusual_token_count.sum()} tokens marked"
            )
        return df

    def delete_unusual_rows_action(self, df: pd.DataFrame, add_history_entry: bool = True, **kwargs) -> pd.DataFrame:

        unusual_tokens = kwargs.get("unusual_tokens", None)
        unusual_token_count = kwargs.get("unusual_token_count", None)

        if unusual_token_count is not None:
            for col in df.columns:
                if unusual_token_count[col] == 0:
                    continue
                df[col] = df[col].astype(str).str.strip()

        count = len(df)

        df = df[~df.isin(unusual_tokens).any(axis=1)]

        if add_history_entry:
            self.df_history.add_action(
                action_id=2,
                action_name="delete_unusual_rows",
                args={
                    "unusual_tokens": unusual_tokens,
                    "unusual_token_count": unusual_token_count
                },
                name="Delete Rows With Unusual Tokens",
                desc=f"{count - len(df)} rows deleted"
            )
        return df

    def apply_missingness_pipeline_action(self, df: pd.DataFrame, add_history_entry: bool = True, **kwargs) -> pd.DataFrame:

        mcar_rate = kwargs.get("mcar_rate", None)
        mcar_columns = kwargs.get("mcar_columns", None)
        mar_numeric = kwargs.get("mar_numeric", None)
        mar_categorical = kwargs.get("mar_categorical", None)
        nmar_numeric = kwargs.get("nmar_numeric", None)
        nmar_categorical = kwargs.get("nmar_categorical", None)
        random_state = kwargs.get("random_state", None)
        mode = kwargs.get("mode", None)
        method_order = kwargs.get("method_order", None)

        result_df, missing_mask = run_miss_pipeline(
            df=df,
            mcar_rate=mcar_rate,
            mcar_columns=mcar_columns,
            mar_numeric=mar_numeric,
            mar_categorical=mar_categorical,
            nmar_numeric=nmar_numeric,
            nmar_categorical=nmar_categorical,
            random_state=random_state,
            mode=mode,
            method_order=method_order,
        )

        if add_history_entry:
            colnum = len({*mcar_columns, *nmar_categorical.keys(), *mar_numeric.keys(), *mar_categorical.keys(), *nmar_numeric.keys()})
            self.df_history.add_action(
                action_id=3,
                action_name="apply_missingness_pipeline",
                args={
                    "mcar_rate": mcar_rate,
                    "mcar_columns": mcar_columns,
                    "mar_numeric": mar_numeric,
                    "mar_categorical": mar_categorical,
                    "nmar_numeric": nmar_numeric,
                    "nmar_categorical": nmar_categorical,
                    "random_state": random_state,
                    "mode": mode,
                    "method_order": method_order,
                },
                name="Simulate Missingness On Dataset",
                desc=f"Methods: {", ".join(method_order)}\nMode: {mode}\nSeed: {random_state}\nNumber of columns: {colnum}"
            )

        return result_df

    def apply_mean_imputation_action(self, df: pd.DataFrame, add_history_entry: bool = True, **kwargs) -> pd.DataFrame:
        columns = kwargs.get("columns", None)

        result_df, imputation_mask, vals = impute_mean(
            df=df,
            columns=columns,
        )

        if add_history_entry:
            cols = [col+" : "+str(vals[col]) if len(col) <= 15 else str(col[:15]) + "... : "+str(vals[col]) for col in columns]
            if len(columns) > 5:
                colnum = "\n".join(cols[:5]) + "..."
            else:
                colnum = "\n".join(cols)

            self.df_history.add_action(
                action_id=4,
                action_name="apply_mean_imputation",
                args={
                    "columns": columns,
                },
                name="Mean Imputation",
                desc=f"Columns: {colnum}\nValues imputed: {imputation_mask.sum().sum()}"
            )

        return result_df

    def apply_median_imputation_action(self, df: pd.DataFrame, add_history_entry: bool = True,
                                     **kwargs) -> pd.DataFrame:
        columns = kwargs.get("columns", None)

        result_df, imputation_mask, vals = impute_median(
            df=df,
            columns=columns,
        )

        if add_history_entry:
            cols = [col+" : "+str(vals[col]) if len(col) <= 15 else str(col[:15]) + "... : "+str(vals[col]) for col in columns]
            if len(columns) > 5:
                colnum = "\n".join(cols[:5]) + "..."
            else:
                colnum = "\n".join(cols)

            self.df_history.add_action(
                action_id=5,
                action_name="apply_median_imputation",
                args={
                    "columns": columns,
                },
                name="Median Imputation",
                desc=f"Columns: {colnum}\nValues imputed: {imputation_mask.sum().sum()}"
            )

        return result_df

    def apply_mode_imputation_action(self, df: pd.DataFrame, add_history_entry: bool = True,
                                     **kwargs) -> pd.DataFrame:
        columns = kwargs.get("columns", None)

        result_df, imputation_mask, vals = impute_mode(
            df=df,
            columns=columns,
        )

        if add_history_entry:
            cols = [col+" : "+str(vals[col]) if len(col) <= 15 else str(col[:15]) + "... : "+str(vals[col]) for col in columns]
            if len(columns) > 5:
                colnum = "\n".join(cols[:5]) + "..."
            else:
                colnum = "\n".join(cols)

            self.df_history.add_action(
                action_id=6,
                action_name="apply_mode_imputation",
                args={
                    "columns": columns,
                },
                name="Mode Imputation",
                desc=f"Columns: {colnum}\nValues imputed: {imputation_mask.sum().sum()}"
            )

        return result_df
