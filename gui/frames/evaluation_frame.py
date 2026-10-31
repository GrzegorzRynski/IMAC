
import customtkinter as ctk
import pandas as pd

from CTkMessagebox import CTkMessagebox

from gui.components.history_view import HistoryView
from init_analitics.init_analytics import infer_column_types
from evaluation.evaluation import (
    imputation_methods_report,
    summarize_comparison_results
)


class EvaluationView(ctk.CTkScrollableFrame):
    def __init__(self, parent, app):
        super().__init__(parent)

        self.app = app
        self.up_to_date = False

        # Evaluation settings
        self.evaluation_mode = ctk.StringVar(value="Single")
        self.auto_selection = ctk.BooleanVar(value=True)

        # Single Evaluation
        self.single_branch_id = None
        self.single_reference_id = None
        self.single_missing_id = None
        self.single_result_id = None

        # Comparison Evaluation
        self.comparison_branch_id = None
        self.comparison_reference_id = None
        self.comparison_missing_id = None

        self.comparison_results = {}
        self.comparison_saved_results = {}

        self.branches = {}
        self.actions = {}

        self.single_branches = None

        self.branches, self.actions = self.get_history_data()
        self.branch_order = list(self.branches.keys())

        self.evaluation_results = {}

        self.load_settings()

        # Title
        ctk.CTkLabel(
            self,
            text="Imputation Evaluation",
            font=("Arial", 24, "bold")
        ).pack(pady=(10, 20))

        # Main content
        self.content_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        self.no_dataset_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        ctk.CTkLabel(
            self.no_dataset_frame,
            text="No Dataset Loaded",
            font=("Arial", 22, "bold")
        ).pack(pady=20)

        self.create_mode_panel()

        self.single_frame = ctk.CTkFrame(
            self.content_frame,
            fg_color="transparent"
        )

        self.comparison_frame = ctk.CTkFrame(
            self.content_frame,
            fg_color="transparent"
        )

        self.create_single_panel()
        self.create_comparison_panel()

        self.create_actions_panel()
        self.history = HistoryView(
            self,
            self.app.manager.df_history,
            self
        )

        self.on_mode_changed(self.evaluation_mode.get())

        # Register update callback
        self.app.manager.register_update_callback(
            self.on_update
        )

        self.app.manager.register_save_callback(
            self.save_settings
        )

        self.app.manager.df_history.register_history_update_callback(
            self.on_update
        )

        self.update_view()

    # ---------------- HISTORY HELPERS ----------------

    def load_settings(self):
        history = self.app.manager.df_history
        settings = self.app.manager.settings.get(
            "evaluation", {}
        )

        auto_selection = settings.get("auto_selection", True)
        self.auto_selection.set(
            auto_selection if auto_selection is not None else True
        )

        current_branch_id = (
            history.branch_ids[history.current_branch]
            if history.branch_ids
               and 0 <= history.current_branch < len(history.branch_ids)
            else None
        )

        # --- SINGLE ---
        single = settings.get("single", {})

        self.single_branch_id = single.get("branch_id")
        if self.single_branch_id is None:
            self.single_branch_id = current_branch_id

        self.single_reference_id = single.get("reference_id")
        if self.single_reference_id is None:
            self.single_reference_id = 0

        self.single_missing_id = single.get("missing_id")
        if self.single_missing_id is None:
            self.single_missing_id = history.current_action_index

        self.single_result_id = single.get("result_id")
        if self.single_result_id is None:
            branch_index = self.get_branch_index(self.single_branch_id)

            if branch_index is not None:
                branch = history.get_history_branch(branch_index)
                self.single_result_id = len(branch) - 1 if branch else None

        # --- COMPARISON ---
        comparison = settings.get("comparison", {})

        self.comparison_branch_id = comparison.get("branch_id")
        if self.comparison_branch_id is None:
            self.comparison_branch_id = current_branch_id

        self.comparison_reference_id = comparison.get("reference_id")
        if self.comparison_reference_id is None:
            self.comparison_reference_id = 0

        self.comparison_missing_id = comparison.get("missing_id")
        if self.comparison_missing_id is None:
            self.comparison_missing_id = history.current_action_index

        self.comparison_saved_results = {
            int(branch_id): action_index
            for branch_id, action_index
            in (comparison.get("results") or {}).items()
        }

    def save_settings(self):
        settings = self.app.manager.settings["evaluation"]

        settings["auto_selection"] = self.auto_selection.get()

        # --- SINGLE ---
        single = settings["single"]

        single["branch_id"] = self.single_branch_id
        single["reference_id"] = self.single_reference_id
        single["missing_id"] = self.single_missing_id
        single["result_id"] = self.single_result_id

        # --- COMPARISON ---
        comparison = settings["comparison"]

        comparison["branch_id"] = self.comparison_branch_id
        comparison["reference_id"] = self.comparison_reference_id
        comparison["missing_id"] = self.comparison_missing_id

        comparison["results"] = {
            str(branch_id): result["action_index"]
            for branch_id, result in self.comparison_results.items()
        }

    def get_history_data(self):
        history = self.app.manager.df_history

        branches = {}
        actions = {}

        for branch_index, branch in enumerate(history.branches):
            branch_id = history.branch_ids[branch_index]

            branches[branch_id] = history.branch_names[branch_index]
            actions[branch_id] = {}

            for action_index, action in enumerate(branch):
                actions[branch_id][action_index] = {
                    "name": action.get("name"),
                    "action_id": action.get("id")
                }

        return branches, actions

    def get_branch_index(self, branch_id):
        history = self.app.manager.df_history

        try:
            return history.branch_ids.index(branch_id)
        except ValueError:
            return None

    def suggest_evaluation_states(self, branch_id):
        if branch_id not in self.actions:
            return None

        actions = self.actions[branch_id]
        history = self.app.manager.df_history

        # Search missingness actions from the end of the branch.
        for missing_index in range(len(actions) - 1, 0, -1):
            missing_action = actions[missing_index]

            if not history.is_missingness_action(missing_action["action_id"]):
                continue

            # Find the last imputation action after this missingness.
            result_index = None

            for index in range(missing_index + 1, len(actions)):
                action = actions[index]

                if history.is_imputation_action(action["action_id"]):
                    result_index = index

            # This missingness action has no imputation after it.
            if result_index is None:
                continue

            reference_index = missing_index
            while reference_index > 0 and history.is_missingness_action(actions[reference_index]["action_id"]):
                reference_index -= 1

            return {
                "reference": reference_index,
                "missing": missing_index,
                "result": result_index
            }

        return None

    def set_action_combobox(self, combobox, choices, action_index):
        label = next(
            (
                label
                for label, index in choices.items()
                if index == action_index
            ),
            ""
        )

        combobox.set(label)

    def auto_select_single(self):
        suggestion = self.suggest_evaluation_states(
            self.single_branch_id
        )

        if suggestion is None:
            return

        self.single_reference_id = suggestion["reference"]
        self.single_missing_id = suggestion["missing"]
        self.single_result_id = suggestion["result"]

        self.set_action_combobox(
            self.single_reference_combobox,
            self.single_reference_choices,
            self.single_reference_id
        )

        self.set_action_combobox(
            self.single_missing_combobox,
            self.single_reference_choices,
            self.single_missing_id
        )

        self.set_action_combobox(
            self.single_result_combobox,
            self.single_reference_choices,
            self.single_result_id
        )

        self.update_single_selection_widgets()

    def auto_select_comparison(self):
        suggestion = self.suggest_evaluation_states(
            self.comparison_branch_id
        )

        if suggestion is None:
            return

        self.comparison_reference_id = suggestion["reference"]
        self.comparison_missing_id = suggestion["missing"]

        self.set_action_combobox(
            self.comparison_reference_combobox,
            self.comparison_action_choices,
            self.comparison_reference_id
        )

        self.set_action_combobox(
            self.comparison_missing_combobox,
            self.comparison_action_choices,
            self.comparison_missing_id
        )

        self.update_comparison_selection_widgets()

    def on_auto_selection_changed(self):
        if self.auto_selection.get():
            if self.evaluation_mode.get() == "Single":
                self.auto_select_single()
            else:
                self.auto_select_comparison()

                for branch_id, result in self.comparison_results.items():
                    suggestion = self.suggest_evaluation_states(
                        branch_id
                    )

                    action_index = (
                        suggestion["result"]
                        if suggestion is not None
                        else None
                    )

                    if action_index is None:
                        continue

                    result["action_index"] = action_index

                    action_choices = {
                        f"{index}. {action['name']}": action_index
                        for index, (action_index, action)
                        in enumerate(self.actions[branch_id].items(), start=1)
                    }

                    self.set_action_combobox(
                        result["combobox"],
                        action_choices,
                        action_index
                    )

        self.app.manager.save_app_data()

    # ---------------- GUI ----------------

    def create_mode_panel(self):
        panel = ctk.CTkFrame(self.content_frame)
        panel.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            panel,
            text="Evaluation Mode",
            font=("Arial", 18, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        ctk.CTkSegmentedButton(
            panel,
            values=["Single", "Comparison"],
            variable=self.evaluation_mode,
            command=self.on_mode_changed
        ).pack(fill="x", padx=15, pady=(5, 15))

    def create_single_panel(self):
        panel = ctk.CTkFrame(self.single_frame)
        panel.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            panel,
            text="History Selection",
            font=("Arial", 18, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        ctk.CTkCheckBox(
            panel,
            text="Auto Selection",
            variable=self.auto_selection,
            command=self.on_auto_selection_changed
        ).pack(anchor="w", padx=15, pady=(5, 10))

        ctk.CTkLabel(
            panel,
            text="Select branch",
            font=("Arial", 16, "bold")
        ).pack(anchor="w", padx=15)

        self.single_branch_choices = {
            f"{index}. {name}": id_val for index, (id_val, name) in enumerate(self.branches.items(), start=1)
        }

        self.single_branch_combobox = ctk.CTkComboBox(
            panel,
            state="readonly",
            values=list(self.single_branch_choices.keys()),
            command=lambda val: self.on_branch_changed(self.single_branch_choices[val])
        )
        self.single_branch_combobox.pack(anchor="w", padx=15, pady=(5, 10))
        self.single_branch_combobox.set(
            next(
                (display for display, id_val in self.single_branch_choices.items() if id_val == self.single_branch_id), ""
            )
        )

        # Reference
        ctk.CTkLabel(
            panel,
            text="Reference Dataset"
        ).pack(anchor="w", padx=15)

        self.single_reference_choices = {
            f"{index}. {action["name"]}": id_val for index, (id_val, action) in enumerate(self.actions[self.single_branch_id].items(), start=1)
        }

        self.single_reference_combobox = ctk.CTkComboBox(
            panel,
            state="readonly",
            values=list(self.single_reference_choices.keys()),
            command=lambda val: self.on_reference_changed(self.single_reference_choices[val])
        )
        self.single_reference_combobox.pack(
            fill="x",
            padx=15,
            pady=(5, 10)
        )
        self.single_reference_combobox.set(
            next(
                    (display for display, id_val in self.single_reference_choices.items() if id_val == self.single_reference_id), ""
            )
        )

        # Missing
        ctk.CTkLabel(
            panel,
            text="Missing Dataset"
        ).pack(anchor="w", padx=15)

        self.single_missing_combobox = ctk.CTkComboBox(
            panel,
            state="readonly",
            values=list(self.single_reference_choices.keys()),
            command=lambda val: self.on_missing_changed(self.single_reference_choices[val])
        )
        self.single_missing_combobox.pack(
            fill="x",
            padx=15,
            pady=(5, 10)
        )
        self.single_missing_combobox.set(
            next(
                    (display for display, id_val in self.single_reference_choices.items() if id_val == self.single_missing_id), ""
            )
        )

        # Result
        ctk.CTkLabel(
            panel,
            text="Imputed Result"
        ).pack(anchor="w", padx=15)

        self.single_result_combobox = ctk.CTkComboBox(
            panel,
            state="readonly",
            values=list(self.single_reference_choices.keys()),
            command=lambda val: self.on_result_changed(self.single_reference_choices[val])
        )
        self.single_result_combobox.pack(
            fill="x",
            padx=15,
            pady=(5, 10)
        )
        self.single_result_combobox.set(
            next(
                    (display for display, id_val in self.single_reference_choices.items() if id_val == self.single_result_id), ""
            )
        )

    def create_comparison_panel(self):
        panel = ctk.CTkFrame(self.comparison_frame)
        panel.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            panel,
            text="History Selection",
            font=("Arial", 18, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        ctk.CTkCheckBox(
            panel,
            text="Auto Selection",
            variable=self.auto_selection,
            command=self.on_auto_selection_changed
        ).pack(anchor="w", padx=15, pady=(5, 10))

        # Main Branch
        ctk.CTkLabel(
            panel,
            text="Main Branch",
            font=("Arial", 16, "bold")
        ).pack(anchor="w", padx=15)

        self.comparison_branch_choices = {
            f"{index}. {name}": branch_id
            for index, (branch_id, name)
            in enumerate(self.branches.items(), start=1)
        }

        self.comparison_branch_combobox = ctk.CTkComboBox(
            panel,
            state="readonly",
            values=list(self.comparison_branch_choices.keys()),
            command=lambda val: self.on_branch_changed(
                self.comparison_branch_choices[val]
            )
        )
        self.comparison_branch_combobox.pack(
            fill="x", padx=15, pady=(5, 10)
        )

        # Reference
        ctk.CTkLabel(
            panel,
            text="Reference Dataset"
        ).pack(anchor="w", padx=15)

        self.comparison_reference_combobox = ctk.CTkComboBox(
            panel,
            state="readonly",
            values=[],
            command=lambda val: self.on_reference_changed(
                self.comparison_action_choices[val]
            )
        )
        self.comparison_reference_combobox.pack(
            fill="x", padx=15, pady=(5, 10)
        )

        self.comparison_action_choices = {
            f"{index}. {action['name']}": action_index
            for index, (action_index, action)
            in enumerate(self.actions[self.comparison_branch_id].items(), start=1)
        }

        # Missing
        ctk.CTkLabel(
            panel,
            text="Missing Dataset"
        ).pack(anchor="w", padx=15)

        self.comparison_missing_combobox = ctk.CTkComboBox(
            panel,
            state="readonly",
            values=[],
            command=lambda val: self.on_missing_changed(
                self.comparison_action_choices[val]
            )
        )
        self.comparison_missing_combobox.pack(
            fill="x", padx=15, pady=(5, 15)
        )

        # Results section
        ctk.CTkLabel(
            panel,
            text="Imputed Results",
            font=("Arial", 18, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 10))

        self.comparison_results_frame = ctk.CTkFrame(
            panel,
            fg_color="transparent"
        )

        # Add Result
        self.comparison_add_result_frame = ctk.CTkFrame(
            panel,
            fg_color="transparent"
        )
        self.comparison_add_result_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.comparison_add_branch_combobox = ctk.CTkComboBox(
            self.comparison_add_result_frame,
            state="readonly",
            values=[]
        )
        self.comparison_add_branch_combobox.pack(
            side="left", fill="x", expand=True, padx=(0, 10)
        )

        ctk.CTkButton(
            self.comparison_add_result_frame,
            text="Add Result",
            width=110,
            command=self.add_comparison_result
        ).pack(side="right")

        # Initialize selection
        if self.branches:
            branch_id = (
                self.comparison_branch_id
                if self.comparison_branch_id in self.branches
                else next(iter(self.branches))
            )

            self.comparison_branch_id = branch_id

            self.comparison_branch_combobox.set(
                next(
                    label for label, value
                    in self.comparison_branch_choices.items()
                    if value == branch_id
                )
            )

            self.restore_comparison_results()
            self.update_comparison_selection_widgets()
            self.update_comparison_result_available_branches()

    def restore_comparison_results(self):
        for branch_id, action_index in self.comparison_saved_results.items():
            self.add_comparison_result(
                branch_id=branch_id,
                action_index=action_index,
                auto_suggest=False
            )

    def create_actions_panel(self):
        self.actions_panel = ctk.CTkFrame(
            self.content_frame,
            fg_color="transparent"
        )
        self.actions_panel.pack(pady=(15, 10))

        ctk.CTkButton(
            self.actions_panel,
            text="Evaluate",
            width=150,
            height=38,
            font=("Arial", 14, "bold"),
            command=self.on_evaluation
        ).pack()

        # Evaluation results container
        self.evaluation_result_frame = ctk.CTkFrame(
            self.content_frame,
            fg_color=("gray90", "gray17"),
            corner_radius=12
        )

    def create_result_section(self, title):
        section = ctk.CTkFrame(
            self.evaluation_result_frame,
            fg_color=("gray85", "gray20"),
            corner_radius=10
        )

        section.pack(
            fill="x",
            padx=15,
            pady=8
        )

        ctk.CTkLabel(
            section,
            text=title,
            font=("Arial", 17, "bold"),
            anchor="w"
        ).pack(
            fill="x",
            padx=15,
            pady=(12, 8)
        )

        return section

    def clear_evaluation_result_frame(self):
        for widget in self.evaluation_result_frame.winfo_children():
            widget.destroy()

        self.evaluation_result_frame.pack_forget()

    def create_result_table(self, parent, headers, rows):
        table = ctk.CTkFrame(
            parent,
            fg_color="transparent",
            corner_radius=8
        )
        table.pack(fill="x", padx=12, pady=(0, 12))

        column_count = len(headers)

        table.grid_columnconfigure(0, weight=2, uniform="table_columns")

        for column in range(1, column_count):
            table.grid_columnconfigure(
                column,
                weight=1,
                uniform="table_columns"
            )

        header_frame = ctk.CTkFrame(
            table,
            fg_color=("gray75", "gray25"),
            corner_radius=6
        )
        header_frame.pack(fill="x")

        for column, header in enumerate(headers):
            ctk.CTkLabel(
                header_frame,
                text=header,
                font=("Arial", 13, "bold"),
                anchor="w" if column == 0 else "e"
            ).grid(
                row=0,
                column=column,
                sticky="ew",
                padx=12,
                pady=10
            )

            header_frame.grid_columnconfigure(
                column,
                weight=2 if column == 0 else 1,
                uniform="table_columns"
            )

        for row_index, row in enumerate(rows):
            row_frame = ctk.CTkFrame(
                table,
                fg_color=(
                    ("gray95", "gray22")
                    if row_index % 2 == 0
                    else ("gray90", "gray18")
                ),
                corner_radius=5
            )
            row_frame.pack(fill="x", pady=(3, 0))

            for column_index, value in enumerate(row):
                ctk.CTkLabel(
                    row_frame,
                    text=str(value),
                    font=("Arial", 13),
                    anchor="w" if column_index == 0 else "e"
                ).grid(
                    row=0,
                    column=column_index,
                    sticky="ew",
                    padx=12,
                    pady=9
                )

                row_frame.grid_columnconfigure(
                    column_index,
                    weight=2 if column_index == 0 else 1,
                    uniform="table_columns"
                )

    def display_single_results(self, results):
        self.clear_evaluation_result_frame()

        report = results["report"]
        coverage = report["coverage"]

        self.evaluation_result_frame.pack(
            fill="x",
            padx=10,
            pady=(5, 20)
        )

        # Main title
        ctk.CTkLabel(
            self.evaluation_result_frame,
            text="Evaluation Results",
            font=("Arial", 22, "bold")
        ).pack(
            anchor="w",
            padx=20,
            pady=(18, 5)
        )

        ctk.CTkLabel(
            self.evaluation_result_frame,
            text=f"Method: {results['method_name']}",
            font=("Arial", 14),
            text_color=("gray35", "gray75")
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 12)
        )

        # Coverage
        coverage_section = self.create_result_section("Coverage")

        coverage_rows = []

        for category, label in [
            ("numeric", "Numeric"),
            ("categorical", "Categorical"),
            ("overall", "Overall")
        ]:
            values = coverage[category]

            percentage = (
                f"{values['coverage']:.2%}"
                if values["coverage"] is not None
                else "N/A"
            )

            coverage_rows.append([
                label,
                percentage,
                values["imputed"],
                values["total"]
            ])

        self.create_result_table(
            coverage_section,
            ["Category", "Coverage", "Imputed", "Missing"],
            coverage_rows
        )

        # Numeric evaluation
        numeric_section = self.create_result_section(
            "Numeric Evaluation"
        )

        numeric_rows = []

        for column, metrics in report["numeric"].items():
            numeric_rows.append([
                column,
                f"{metrics['MAE']:.4f}",
                f"{metrics['RMSE']:.4f}",
                (
                    f"{metrics['NRMSE']:.4f}"
                    if metrics["NRMSE"] is not None
                    else "N/A"
                )
            ])

        if numeric_rows:
            self.create_result_table(
                numeric_section,
                ["Column", "MAE", "RMSE", "NRMSE"],
                numeric_rows
            )
        else:
            ctk.CTkLabel(
                numeric_section,
                text="No numeric columns to evaluate.",
                text_color=("gray40", "gray70")
            ).pack(
                anchor="w",
                padx=15,
                pady=(0, 15)
            )

        # Categorical evaluation
        categorical_section = self.create_result_section(
            "Categorical Evaluation"
        )

        categorical_rows = []

        for column, metrics in report["categorical"].items():
            categorical_rows.append([
                column,
                f"{metrics['Accuracy']:.4f}",
                f"{metrics['MacroF1']:.4f}"
            ])

        if categorical_rows:
            self.create_result_table(
                categorical_section,
                ["Column", "Accuracy", "Macro F1"],
                categorical_rows
            )
        else:
            ctk.CTkLabel(
                categorical_section,
                text="No categorical columns to evaluate.",
                text_color=("gray40", "gray70")
            ).pack(
                anchor="w",
                padx=15,
                pady=(0, 15)
            )

    def add_comparison_result(self, branch_id=None, action_index=None, auto_suggest=True):
        if branch_id is None:
            selected = self.comparison_add_branch_combobox.get()
            branch_id = self.comparison_add_branch_choices.get(selected)

        if (
                branch_id is None
                or branch_id not in self.branches
                or branch_id in self.comparison_results
                or branch_id == self.comparison_branch_id
        ):
            return

        if (
                action_index is None
                and auto_suggest
                and self.auto_selection.get()
        ):
            suggestion = self.suggest_evaluation_states(branch_id)

            if suggestion is not None:
                action_index = suggestion["result"]

        # Result container
        result_frame = ctk.CTkFrame(
            self.comparison_results_frame
        )
        result_frame.pack(fill="x", pady=(0, 10))

        # Header
        header = ctk.CTkFrame(
            result_frame,
            fg_color="transparent"
        )
        header.pack(fill="x", padx=10, pady=(10, 5))

        branch_label = ctk.CTkLabel(
            header,
            text=self.branches[branch_id],
            font=("Arial", 15, "bold")
        )
        branch_label.pack(side="left")

        ctk.CTkButton(
            header,
            text="Remove",
            width=80,
            fg_color="#A83232",
            hover_color="#842727",
            command=lambda bid=branch_id: (
                self.remove_comparison_result(bid)
            )
        ).pack(side="right")

        # Action choices
        action_choices = {
            f"{index}. {action['name']}": action_index
            for index, (action_index, action)
            in enumerate(self.actions[branch_id].items(), start=1)
        }

        action_combobox = ctk.CTkComboBox(
            result_frame,
            state="readonly",
            values=list(action_choices.keys()),
            command=lambda val, bid=branch_id: (
                self.on_comparison_result_changed(
                    bid,
                    action_choices[val]
                )
            )
        )
        action_combobox.pack(
            fill="x", padx=10, pady=(5, 10)
        )

        selected_label = next(
            (
                label for label, value in action_choices.items()
                if value == action_index
            ),
            ""
        )

        action_combobox.set(selected_label)

        self.comparison_results[branch_id] = {
            "action_index": action_index if selected_label else None,
            "frame": result_frame,
            "combobox": action_combobox,
            "label": branch_label
        }

        if len(self.comparison_results) == 1:
            self.comparison_results_frame.pack(
                fill="x",
                padx=15,
                pady=(0, 10),
                before=self.comparison_add_result_frame
            )

        self.update_comparison_result_available_branches()

    def on_comparison_result_changed(self, branch_id, action_index):
        self.comparison_results[branch_id]["action_index"] = action_index

    def update_comparison_result_comboboxes(self):
        for branch_id, comparison_result in list(self.comparison_results.items()):
            if (
                    branch_id not in self.branches
                    or branch_id == self.comparison_branch_id
            ):
                self.remove_comparison_result(branch_id)
                continue

            comparison_result["label"].configure(text=self.branches[branch_id])

            action_choices = {
                f"{index}. {action['name']}": action_index
                for index, (action_index, action)
                in enumerate(self.actions[branch_id].items(), start=1)
            }

            combobox = comparison_result["combobox"]
            combobox.configure(values=list(action_choices.keys()))

            selected_label = next(
                (
                    label
                    for label, action_index in action_choices.items()
                    if action_index == comparison_result["action_index"]
                ),
                ""
            )

            combobox.set(selected_label)

            if not selected_label:
                comparison_result["action_index"] = None

    def remove_comparison_result(self, branch_id):
        result = self.comparison_results.pop(branch_id, None)

        if result is None:
            return

        result["frame"].destroy()

        if len(self.comparison_results) == 0:
            self.comparison_results_frame.pack_forget()

        self.update_comparison_result_available_branches()

    def update_comparison_result_available_branches(self):
        self.comparison_add_branch_choices = {
            f"{index}. {name}": branch_id
            for index, (branch_id, name)
            in enumerate(self.branches.items(), start=1)
            if (
                    branch_id != self.comparison_branch_id
                    and branch_id not in self.comparison_results
            )
        }

        values = list(self.comparison_add_branch_choices.keys())

        self.comparison_add_branch_combobox.configure(
            values=values
        )

        self.comparison_add_branch_combobox.set(
            values[0] if values else ""
        )

    def update_comparison_selection_widgets(self):
        branch_id = self.comparison_branch_id

        if branch_id not in self.actions:
            return

        self.comparison_action_choices = {
            f"{index}. {action['name']}": action_index
            for index, (action_index, action)
            in enumerate(self.actions[branch_id].items(), start=1)
        }

        values = list(self.comparison_action_choices.keys())

        self.comparison_reference_combobox.configure(values=values)
        self.comparison_missing_combobox.configure(values=values)

        if self.comparison_reference_combobox.get() not in self.comparison_action_choices:
            self.comparison_reference_combobox.set("")
            self.comparison_reference_id = None

        if self.comparison_missing_combobox.get() not in self.comparison_action_choices:
            self.comparison_missing_combobox.set("")
            self.comparison_missing_id = None

    def update_single_selection_widgets(self):
        branch_id = self.single_branch_id

        if branch_id not in self.actions:
            return

        self.single_reference_choices = {
            f"{index}. {action["name"]}": id_val for index, (id_val, action) in
            enumerate(self.actions[branch_id].items(), start=1)
        }

        self.single_reference_combobox.configure(values=list(self.single_reference_choices.keys()))
        self.single_missing_combobox.configure(values=list(self.single_reference_choices.keys()))
        self.single_result_combobox.configure(values=list(self.single_reference_choices.keys()))

        if self.single_reference_combobox.get() not in self.single_reference_choices:
            self.single_reference_combobox.set("")
            self.single_reference_id = None

        if self.single_missing_combobox.get() not in self.single_reference_choices:
            self.single_missing_combobox.set("")
            self.single_missing_id = None

        if self.single_result_combobox.get() not in self.single_reference_choices:
            self.single_result_combobox.set("")
            self.single_result_id = None

    def update_branches(self):
        self.single_branch_choices = {
            f"{index}. {name}": branch_id
            for index, (branch_id, name)
            in enumerate(self.branches.items(), start=1)
        }

        self.comparison_branch_choices = self.single_branch_choices.copy()

        values = list(self.single_branch_choices.keys())

        self.single_branch_combobox.configure(values=values)
        self.comparison_branch_combobox.configure(values=values)

        if not self.branches:
            self.single_branch_id = None
            self.comparison_branch_id = None

            self.single_branch_combobox.set("")
            self.comparison_branch_combobox.set("")
            return

        history = self.app.manager.df_history

        current_branch_id = (
            history.branch_ids[history.current_branch]
            if history.branch_ids
               and 0 <= history.current_branch < len(history.branch_ids)
            else None
        )

        fallback_branch_id = (
            current_branch_id
            if current_branch_id is None or current_branch_id in self.branches
            else next(iter(self.branches))
        )

        if self.single_branch_id not in self.branches:
            self.single_branch_id = fallback_branch_id

        if self.comparison_branch_id not in self.branches:
            self.comparison_branch_id = fallback_branch_id

        for label, branch_id in self.single_branch_choices.items():
            if branch_id == self.single_branch_id:
                self.single_branch_combobox.set(label)

            if branch_id == self.comparison_branch_id:
                self.comparison_branch_combobox.set(label)

        self.update_single_selection_widgets()
        self.update_comparison_selection_widgets()
        self.update_comparison_result_comboboxes()
        self.update_comparison_result_available_branches()

    def on_branch_changed(self, branch_id):
        if self.evaluation_mode.get() == "Single":
            if self.single_branch_id == branch_id:
                return
            self.single_branch_id = branch_id
            self.update_single_selection_widgets()

            if self.auto_selection.get():
                self.auto_select_single()

        else:
            if self.comparison_branch_id == branch_id:
                return
            self.comparison_branch_id = branch_id

            self.update_comparison_selection_widgets()
            self.update_comparison_result_available_branches()
            self.update_comparison_result_comboboxes()

            if self.auto_selection.get():
                self.auto_select_comparison()

    def on_reference_changed(self, value):
        if self.evaluation_mode.get() == "Single":
            self.single_reference_id = value
        else:
            self.comparison_reference_id = value

    def on_missing_changed(self, value):
        if self.evaluation_mode.get() == "Single":
            self.single_missing_id = value
        else:
            self.comparison_missing_id = value

    def on_result_changed(self, value):
        if self.evaluation_mode.get() == "Single":
            self.single_result_id = value

    def on_mode_changed(self, mode):
        self.single_frame.pack_forget()
        self.comparison_frame.pack_forget()
        self.actions_panel.pack_forget()

        if mode == "Single":
            self.single_frame.pack(fill="both", expand=True)
        else:
            self.comparison_frame.pack(fill="both", expand=True)

        self.actions_panel.pack(pady=20)

    # ---------------- EVALUATION ----------------

    def validate_evaluation_selection(self):
        history = self.app.manager.df_history

        if self.evaluation_mode.get() == "Single":
            branch_id = self.single_branch_id
            reference_id = self.single_reference_id
            missing_id = self.single_missing_id
            result_ids = [self.single_result_id]

        else:
            branch_id = self.comparison_branch_id
            reference_id = self.comparison_reference_id
            missing_id = self.comparison_missing_id

            if not self.comparison_results:
                raise ValueError("Add at least one imputation result.")

            result_ids = [
                result["action_index"]
                for result in self.comparison_results.values()
            ]

        if branch_id is None or branch_id not in self.actions:
            raise ValueError("Selected branch no longer exists.")

        if reference_id is None or missing_id is None:
            raise ValueError("Select reference and missing datasets.")

        if reference_id >= missing_id:
            raise ValueError(
                "Reference dataset must be selected before missing dataset."
            )

        main_actions = self.actions[branch_id]

        if missing_id not in main_actions:
            raise ValueError("Invalid missing dataset selection.")

        if not history.is_missingness_action(
                main_actions[missing_id]["action_id"]
        ):
            raise ValueError(
                "Selected missing dataset does not represent a missingness action."
            )

        for index in result_ids:
            if index is not None and index <= missing_id:
                raise ValueError(
                    "Imputation result must be selected after missing dataset."
                )

        if self.evaluation_mode.get() == "Single":
            if result_ids[0] is None:
                raise ValueError("Selected result dataset.")

            result_action = main_actions[result_ids[0]]

            if not history.is_imputation_action(result_action["action_id"]):
                raise ValueError(
                    "Selected result is not an imputation action."
                )

        else:
            if all([
                result["action_index"] is None
                for result in self.comparison_results.values()
            ]):
                raise ValueError("At least one result action must be selected.")

            for branch_id, result in self.comparison_results.items():
                if branch_id not in self.actions:
                    raise ValueError(
                        f"Branch '{self.branches.get(branch_id, branch_id)}' no longer exists."
                    )

                actions = self.actions[branch_id]
                result_index = result["action_index"]
                if result_index is None:
                    continue

                if result_index not in actions:
                    raise ValueError(
                        f"Invalid result selection in branch '{self.branches[branch_id]}'."
                    )

                if not history.is_imputation_action(
                        actions[result_index]["action_id"]
                ):
                    raise ValueError(
                        f"Selected result in branch '{self.branches[branch_id]}' "
                        "is not an imputation action."
                    )

                for index in range(missing_id + 1):
                    if (
                            index not in main_actions
                            or index not in actions
                            or main_actions[index] != actions[index]
                    ):
                        raise ValueError(
                            f"Branch '{self.branches[branch_id]}' "
                            "does not share the same history up to the missingness action."
                        )

    def prepare_evaluation_data(self):
        manager = self.app.manager

        self.validate_evaluation_selection()

        if self.evaluation_mode.get() == "Single":
            branch_id = self.single_branch_id

            if None in (
                    self.single_reference_id,
                    self.single_missing_id,
                    self.single_result_id
            ):
                raise ValueError("Complete all dataset selections.")

            valid_result_states = {
                self.branches[branch_id]: (
                    branch_id,
                    self.single_result_id
                )
            }

            reference_id = self.single_reference_id
            missing_id = self.single_missing_id

        else:
            branch_id = self.comparison_branch_id

            if None in (
                    self.comparison_reference_id,
                    self.comparison_missing_id
            ):
                raise ValueError("Select reference and missing datasets.")

            if not self.comparison_results:
                raise ValueError("Add at least one imputation result.")

            reference_id = self.comparison_reference_id
            missing_id = self.comparison_missing_id

            result_states = {
                self.branches[result_branch_id]: (
                    result_branch_id,
                    result["action_index"]
                )
                for result_branch_id, result
                in self.comparison_results.items()
            }

            valid_result_states = {
                key: value for key, value in result_states.items()
                if value[1] is not None
            }

            if not valid_result_states:
                raise ValueError("No imputation results selected.")

        branch_index = self.get_branch_index(branch_id)

        if branch_index is None:
            raise ValueError("Selected branch no longer exists.")

        df_reference = manager.get_dataset_state(
            branch_index,
            reference_id
        )

        df_missing = manager.get_dataset_state(
            branch_index,
            missing_id
        )

        imputed_datasets = {}

        for name, (result_branch_id, action_index) in valid_result_states.items():
            result_branch_index = self.get_branch_index(result_branch_id)

            if result_branch_index is None:
                raise ValueError(f"Branch '{name}' no longer exists.")

            imputed_datasets[name] = manager.get_dataset_state(
                result_branch_index,
                action_index
            )

        # Validate dataset structure
        for name, df in {
            "Missing": df_missing,
            **imputed_datasets
        }.items():
            if (
                    not df.index.equals(df_reference.index)
                    or not df.columns.equals(df_reference.columns)
            ):
                raise ValueError(
                    f"Dataset '{name}' has different indexes or columns."
                )

        # Identify artificially missing values
        mask_missing = (
                df_missing.isna()
                & df_reference.notna()
        )

        if not mask_missing.to_numpy().any():
            raise ValueError("No artificially missing values found.")

        column_types = infer_column_types(df_reference)

        return {
            "reference": df_reference,
            "missing": df_missing,
            "mask": mask_missing,
            "results": imputed_datasets,
            "column_types": column_types
        }

    def evaluate(self):
        try:
            data = self.prepare_evaluation_data()

            numeric_columns = data["column_types"]["numeric"]
            categorical_columns = data["column_types"]["categorical"]

            method_results = imputation_methods_report(
                df_reference=data["reference"],
                df_missing=data["missing"],
                imputed_datasets=data["results"],
                numeric_columns=numeric_columns,
                categorical_columns=categorical_columns
            )
        except ValueError as e:
            return None

        if self.evaluation_mode.get() == "Single":
            method_name, report = next(iter(method_results.items()))

            evaluation_results = {
                "method_name": method_name,
                "report": report
            }

        else:
            summary = summarize_comparison_results(method_results)

            evaluation_results = {
                "methods": method_results,
                "summary": summary
            }

        return evaluation_results

    def on_evaluation(self):
        result = self.evaluate()

        if result is None:
            return

        if self.evaluation_mode.get() == "Single":
            self.evaluation_results["Single"] = result

            self.clear_evaluation_result_frame()
            self.display_single_results(result)

    # ---------------- UPDATE ----------------

    def on_update(self):
        self.up_to_date = False
        self.update_view()

    def update_view(self):
        if self.app.current_view == self and not self.up_to_date:
            self.up_to_date = True

            df = self.app.manager.current_df

            if df is None:
                self.content_frame.pack_forget()
                self.history.pack_forget()
                self.no_dataset_frame.pack(pady=20)
                return

            self.no_dataset_frame.pack_forget()

            self.content_frame.pack(
                fill="both",
                padx=20,
                pady=10
            )

            self.history.pack(fill="both", expand=True)
            self.history.render_history()

            self.on_mode_changed(self.evaluation_mode.get())

            branches, actions = self.get_history_data()
            new_order = list(branches.keys())

            if (
                    self.branches != branches
                    or self.actions != actions
                    or self.branch_order != new_order
            ):
                self.branches = branches
                self.actions = actions
                self.branch_order = new_order

                self.update_branches()


