import customtkinter as ctk
import pandas as pd

from gui.components.history_view import HistoryView


class ImputationView(ctk.CTkScrollableFrame):

    METHODS = {
        "Mean": {
            "description": "Replace missing values with the mean of each selected numeric column.",
            "column_type": "numeric",
            "parameters": {}
        },
        "Median": {
            "description": "Replace missing values with the median of each selected numeric column.",
            "column_type": "numeric",
            "parameters": {}
        },
        "Mode": {
            "description": "Replace missing values with the most frequent value in each selected column.",
            "column_type": "all",
            "parameters": {}
        },
        # "KNN": {
        #     "description": "Estimate missing values using the nearest neighboring samples.",
        #     "column_type": "numeric",
        #     "parameters": {
        #         "n_neighbors": {
        #             "type": "int",
        #             "default": 5,
        #             "min": 1,
        #             "max": 50,
        #             "label": "Number of neighbors"
        #         },
        #         "weights": {
        #             "type": "choice",
        #             "default": "uniform",
        #             "values": ["uniform", "distance"],
        #             "label": "Neighbor weights"
        #         }
        #     }
        # }
    }

    def __init__(self, parent, app):
        super().__init__(parent)

        self.app = app
        self.up_to_date = False

        self.selected_method = ctk.StringVar(value="Mean")
        self.column_vars = {}
        self.parameter_vars = {}

        self.current_columns = pd.Index([])
        self.current_col_vars = []

        self.load_settings()

        ctk.CTkLabel(
            self,
            text="Data Imputation",
            font=("Arial", 24, "bold")
        ).pack(pady=(10, 20))

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
        ).pack()

        self.no_missing_data_label = ctk.CTkLabel(
            self,
            text="No Missing Data In Dataset",
            font=("Arial", 22, "bold"),
            text_color="red"
        )

        self.create_method_panel()
        self.create_columns_panel()
        self.create_parameters_panel()
        self.create_footer()

        self.history = HistoryView(
            self,
            self.app.manager.df_history,
            self
        )

        self.app.manager.register_update_callback(
            self.on_update
        )

        self.app.manager.register_save_callback(
            self.save_settings
        )

        self.on_method_changed()
        self.update_view()

    # ---------------- SETTINGS ----------------

    def load_settings(self):
        settings = self.app.manager.settings.get(
            "imputation", {}
        )

        method = settings.get("selected_method", "Mean") or "Mean"

        if method not in self.METHODS:
            method = "Mean"

        self.selected_method.set(method)

        self.selected_columns = settings.get(
            "selected_columns", {}
        ) or {}

        self.selected_parameters = settings.get(
            "method_parameters", {}
        ) or {}

    def save_settings(self):
        settings = self.app.manager.settings["imputation"]

        settings["selected_method"] = (
            self.selected_method.get()
        )

        settings["selected_columns"] = {
            column: var.get()
            for column, var in self.column_vars.items()
        }

        settings["method_parameters"] = {
            method: {
                name: var.get()
                for name, var in parameters.items()
            }
            for method, parameters in self.parameter_vars.items()
        }

    # ---------------- METHOD PANEL ----------------

    def create_method_panel(self):
        panel = ctk.CTkFrame(self.content_frame)
        panel.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            panel,
            text="Imputation Method",
            font=("Arial", 18, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        ctk.CTkComboBox(
            panel,
            values=list(self.METHODS.keys()),
            variable=self.selected_method,
            state="readonly",
            command=lambda _: self.on_method_changed()
        ).pack(fill="x", padx=15, pady=5)

        self.method_description = ctk.CTkLabel(
            panel,
            text="",
            wraplength=600,
            justify="left",
            text_color="gray"
        )

        self.method_description.pack(
            fill="x",
            padx=15,
            pady=(5, 15)
        )

    # ---------------- PARAMETERS PANEL ----------------

    def create_parameters_panel(self):
        self.parameters_panel = ctk.CTkFrame(
            self.content_frame
        )

        self.parameters_panel.pack(
            fill="x",
            padx=10,
            pady=10
        )

        ctk.CTkLabel(
            self.parameters_panel,
            text="Method Parameters",
            font=("Arial", 18, "bold")
        ).pack(anchor="w", padx=15, pady=10)

        self.parameters_content = ctk.CTkFrame(
            self.parameters_panel,
            fg_color="transparent"
        )

        self.parameters_content.pack(
            fill="x",
            padx=15,
            pady=(0, 15)
        )

    def update_parameters_panel(self):
        for widget in self.parameters_content.winfo_children():
            widget.destroy()

        method = self.selected_method.get()
        parameters = self.METHODS[method]["parameters"]

        if not parameters:
            ctk.CTkLabel(
                self.parameters_content,
                text="This method has no additional parameters.",
                text_color="gray"
            ).pack(anchor="w")
            return

        method_vars = self.parameter_vars.setdefault(
            method, {}
        )

        for name, config in parameters.items():
            row = ctk.CTkFrame(
                self.parameters_content,
                fg_color="transparent"
            )
            row.pack(fill="x", pady=5)

            ctk.CTkLabel(
                row,
                text=config["label"],
                width=180,
                anchor="w"
            ).pack(side="left")

            if name not in method_vars:
                saved_value = (
                    self.selected_parameters
                    .get(method, {})
                    .get(name, config["default"])
                )

                if config["type"] == "int":
                    method_vars[name] = ctk.StringVar(
                        value=str(saved_value)
                    )
                else:
                    method_vars[name] = ctk.StringVar(
                        value=str(saved_value)
                    )

            variable = method_vars[name]

            if config["type"] == "choice":
                ctk.CTkComboBox(
                    row,
                    values=config["values"],
                    variable=variable,
                    state="readonly"
                ).pack(side="right")

            elif config["type"] == "int":
                ctk.CTkEntry(
                    row,
                    textvariable=variable,
                    width=120
                ).pack(side="right")

    # ---------------- COLUMNS PANEL ----------------

    def create_columns_panel(self):
        panel = ctk.CTkFrame(self.content_frame)
        panel.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            panel,
            text="Target Columns",
            font=("Arial", 18, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        method = self.selected_method.get()
        column_type = self.METHODS[method]["column_type"]
        label_text = f"Only {column_type} columns" if column_type != "all" else "All column types"

        self.column_type_label = ctk.CTkLabel(
            panel,
            text=label_text,
            text_color="gray"
        )
        self.column_type_label.pack(anchor="w", padx=15, pady=(0, 5))

        actions = ctk.CTkFrame(
            panel,
            fg_color="transparent"
        )
        actions.pack(fill="x", padx=15)

        ctk.CTkButton(
            actions,
            text="Select All",
            width=110,
            command=lambda: self.set_all_columns(True)
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            actions,
            text="Clear All",
            width=110,
            command=lambda: self.set_all_columns(False)
        ).pack(side="left")

        self.columns_content = ctk.CTkScrollableFrame(
            panel,
            height=180
        )
        self.columns_content.pack(
            fill="x",
            padx=15,
            pady=10
        )

    def update_columns_panel(self):
        for widget in self.columns_content.winfo_children():
            widget.destroy()

        df = self.app.manager.current_df

        if df is None:
            return

        method = self.selected_method.get()
        column_type = self.METHODS[method]["column_type"]

        label_text = f"Only {column_type} columns" if column_type != "all" else "All column types"

        self.column_type_label.configure(text=label_text)
        self.current_col_vars.clear()

        for column in self.current_columns:
            if (
                (column_type == "numeric"
                and not pd.api.types.is_numeric_dtype(df[column])) or
                (column_type == "categorical"
                and pd.api.types.is_numeric_dtype(df[column]))
            ):
                continue

            if column not in self.column_vars:
                self.column_vars[column] = ctk.BooleanVar(
                    value=self.selected_columns.get(column, False)
                )

            self.current_col_vars.append(self.column_vars[column])
            label_text = (str(column) + " ( "
                       + str(df[column].isna().sum()) + " Missing, "
                       + str(round(df[column].isna().sum()*100/len(df), 2))) + "% )"

            ctk.CTkCheckBox(
                self.columns_content,
                text=label_text,
                variable=self.column_vars[column]
            ).pack(anchor="w", pady=3)

    def set_all_columns(self, value):
        for column in self.current_col_vars:
            column.set(value)

    # ---------------- FOOTER ----------------

    def create_footer(self):
        self.footer_frame = ctk.CTkFrame(
            self.content_frame,
            fg_color="transparent"
        )

        self.footer_frame.pack(pady=20)

        ctk.CTkButton(
            self.footer_frame,
            text="Reset Settings",
            command=self.reset_settings
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            self.footer_frame,
            text="Apply Imputation",
            command=self.apply_imputation
        ).pack(side="left", padx=5)

    # ---------------- CALLBACKS ----------------

    def on_method_changed(self):
        method = self.selected_method.get()

        self.method_description.configure(
            text=self.METHODS[method]["description"]
        )

        self.update_columns_panel()
        self.update_parameters_panel()

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
                self.no_dataset_frame.pack(pady=10)
                return

            self.no_missing_data_label.pack_forget()

            if df.isna().sum().sum() == 0:
                self.content_frame.pack_forget()
                self.history.pack_forget()
                self.no_missing_data_label.pack()

            self.no_dataset_frame.pack_forget()
            self.content_frame.pack(
                fill="both",
                padx=20,
                pady=10
            )

            self.history.pack_history()
            self.history.render_history()

            if not self.current_columns.equals(df.columns):
                self.current_columns = df.columns.copy()

                self.column_vars = {
                    column: ctk.BooleanVar(
                        value=self.selected_columns.get(column, False)
                    )
                    for column in self.current_columns
                }

            self.update_columns_panel()

    def reset_settings(self):
        self.selected_method.set("Mean")

        for var in self.column_vars.values():
            var.set(False)

        self.parameter_vars.clear()
        self.selected_parameters = {}

        self.on_method_changed()

    def apply_imputation(self):
        df = self.app.manager.current_df

        if df is None:
            return

        method = self.selected_method.get()

        column_type = self.METHODS[method]["column_type"]

        columns = [
            column
            for column, var in self.column_vars.items()
            if var.get()
            and column in self.current_columns
            and (
                column_type == "all" or
               (column_type == "numeric"
                and pd.api.types.is_numeric_dtype(df[column])) or
               (column_type == "categorical"
                and not pd.api.types.is_numeric_dtype(df[column]))
            )
        ]

        if not columns:
            return

        # Only impute columns containing missing values.
        columns = [
            column
            for column in columns
            if df[column].isna().any()
        ]

        if not columns:
            return

        parameters = {}

        for name, config in self.METHODS[method]["parameters"].items():
            value = self.parameter_vars[method][name].get()

            if config["type"] == "int":
                value = int(value)

                if config["min"] > value:
                    value = config["min"]
                elif config["max"] < value:
                    value = config["max"]

            parameters[name] = value

        self.app.manager.apply_imputation(
            method=method,
            columns=columns,
            parameters=parameters
        )

        self.app.manager.save_app_data()