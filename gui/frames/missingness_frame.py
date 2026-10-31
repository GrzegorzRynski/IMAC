import random
from textwrap import fill
from tkinter import font

import customtkinter as ctk
import pandas as pd
from sklearn import pipeline

from gui.components.history_view import HistoryView
from init_analitics.init_analytics import infer_column_types


class MissingnessView(ctk.CTkScrollableFrame):
    def __init__(self, parent, app):
        super().__init__(parent)

        self.app = app

        if self.app.manager.current_df is not None:
            self.current_columns = self.app.manager.current_df.columns
            self.cat_columns = infer_column_types(self.app.manager.current_df)["categorical"]
        else:
            self.current_columns = pd.Series()
            self.cat_columns = []

        self.up_to_date = False

        self.selected_mechanism = ctk.StringVar(value="MCAR")
        self.mcar_missingness_rate_var = ctk.DoubleVar(value=20.0)

        self.methods_active = {}

        self.mar_predictor_var = ctk.StringVar(value="")

        self.base_rates = {}
        self.strengths = {}

        self.column_vars = { "MCAR" : {},
                             "MAR" : {},
                             "NMAR" : {}}

        self.column_checkboxes = {}
        self.cat_column_rates = { "MAR" : {},
                                  "NMAR" : {}}
        self.prev_cat_cols = []
        self.prev_mechanism = ""
        self.method_order = [ctk.StringVar(value="MCAR"), ctk.StringVar(value="MAR") ,ctk.StringVar(value="NMAR")]
        self.seed_var = ctk.StringVar(value="")
        self.seeds = []
        self.always_random_var = ctk.BooleanVar(value=False)
        self.pipeline_var = ctk.StringVar(value="")

        # --- TITLE ---
        title = ctk.CTkLabel(self, text="Missing Data Simulator", font=("Arial", 24, "bold"))
        title.pack(pady=(10, 20))

        # --- CONTENT FRAME ---
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")

        # --- FOOTER FRAME ---
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")

        # --- NO DATASET FRAME ---
        self.no_dataset_frame = ctk.CTkFrame(self, fg_color="transparent")
        no_dataset_label = ctk.CTkLabel(self.no_dataset_frame, text="No Dataset Loaded", font=("Arial", 22, "bold"))
        no_dataset_label.pack(pady=5)

        self.content_frame.grid_columnconfigure((0, 1), weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=0)
        self.content_frame.grid_rowconfigure(2, weight=0)

        self.load_settings()

        self.parameter_frames = {}
        self.create_settings_panel(self.content_frame)

        self.create_columns_panel(self.content_frame)
        self.create_categories_settings_panel(self.content_frame)
        self.create_general_settings_panel(self.content_frame)
        self.create_footer()

        self.history = HistoryView(self, self.app.manager.df_history, self)

        if not self.current_columns.empty:
            self.content_frame.pack(pady=20, padx=20, fill="both")
            self.footer_frame.pack(pady=20)
        else:
            self.no_dataset_frame.pack()

        self.app.manager.register_update_callback(self.on_update)
        self.app.manager.register_save_callback(self.save_settings)

        self.update_view()

    def load_settings(self):
        settings = self.app.manager.settings.get("missingness", {})

        method_settings = settings.get("method_settings", {})

        self.selected_mechanism.set(method_settings.get("selected_mechanism", "MCAR") or "MCAR")
        self.mcar_missingness_rate_var.set(method_settings.get("mcar_missingness_rate", 20.0) or 20.0)

        active_methods = method_settings.get("active_methods", {}) or {}
        if active_methods:
            self.methods_active = {
                method: ctk.BooleanVar(value=value)
                for method, value in active_methods.items()
            }
        else:
            self.methods_active = {
                "MCAR" : ctk.BooleanVar(value=False),
                "MAR": ctk.BooleanVar(value=False),
                "NMAR": ctk.BooleanVar(value=False)
            }

        self.mar_predictor_var.set(
            method_settings.get("mar_predictor")
            or (self.current_columns[0] if len(self.current_columns) > 0 else "")
        )

        base_rates = method_settings.get("base_rates", {}) or {}
        if base_rates:
            self.base_rates = {
                method: ctk.DoubleVar(value=value)
                for method, value in base_rates.items()
            }
        else:
            self.base_rates = {
                "MAR": ctk.DoubleVar(value=10.0),
                "NMAR": ctk.DoubleVar(value=10.0)
            }

        strengths = method_settings.get("strengths", {}) or {}
        if strengths:
            self.strengths = {
                method: ctk.DoubleVar(value=value)
                for method, value in strengths.items()
            }
        else:
            self.strengths = {
                "MAR": ctk.DoubleVar(value=50.0),
                "NMAR": ctk.DoubleVar(value=50.0)
            }

        method_columns = method_settings.get("method_columns", {}) or {}
        if method_columns:
            self.column_vars =  {
                method: {
                    column: ctk.BooleanVar(value=value)
                    for column, value in columns.items()
                }
                for method, columns in method_columns.items()
            }
        else:
            for mechanism in self.column_vars.keys():
                for column in self.current_columns:
                    self.column_vars[mechanism][column] = ctk.BooleanVar(value=False)

        method_categorical_column_rates = method_settings.get("categorical_column_rates", {}) or {}
        if method_categorical_column_rates:
            self.cat_column_rates =  {
                method: {
                    column: {
                        category: ctk.DoubleVar(value=value)
                        for category, value in categories.items()
                    }
                    for column, categories in columns.items()
                }
                for method, columns in method_categorical_column_rates.items()
            }

        method_order = method_settings.get("method_order", []) or []
        if method_order:
            self.method_order = [
                ctk.StringVar(value=method) for method in method_order
            ]
        else:
            self.method_order = [ctk.StringVar(value="MCAR"), ctk.StringVar(value="MAR"), ctk.StringVar(value="NMAR")]

        seed_settings = settings.get("rng_seeds", {}) or {}

        raw_seeds = seed_settings.get("seeds", []) or []

        self.seeds = [s for s in raw_seeds if isinstance(s, str) and s.isdigit()]
        self.seed_var.set(seed_settings.get("current_rng_seed", "") or "")
        self.always_random_var.set(seed_settings.get("always_random_seed", False) or False)
        self.pipeline_var.set(settings.get("pipeline_mode", "Sequential") or "Sequential")

    def save_settings(self):
        settings = self.app.manager.settings["missingness"]
        method_settings = settings["method_settings"]
        rng_seeds = settings["rng_seeds"]

        method_settings["selected_mechanism"] = self.selected_mechanism.get()

        method_settings["mcar_missingness_rate"] = self.mcar_missingness_rate_var.get()

        method_settings["active_methods"] = {
            method: var.get()
            for method, var in self.methods_active.items()
        }

        method_settings["mar_predictor"] = self.mar_predictor_var.get()

        method_settings["base_rates"] = {
            method: var.get()
            for method, var in self.base_rates.items()
        }

        method_settings["strengths"] = {
            method: var.get()
            for method, var in self.strengths.items()
        }

        method_settings["method_columns"] = {
            method: {
                column: var.get()
                for column, var in columns.items()
            }
            for method, columns in self.column_vars.items()
        }

        method_settings["categorical_column_rates"] = {
            method: {
                column: {
                    category : var.get()
                    for category, var in categories.items()
                }
                for column, categories in columns.items()
            }
            for method, columns in self.cat_column_rates.items()
        }

        method_settings["method_order"] = [
            method.get()
            for method in self.method_order
        ]

        rng_seeds["seeds"] = self.seeds
        rng_seeds["current_rng_seed"] = self.seed_var.get()
        rng_seeds["always_random_seed"] = self.always_random_var.get()

        settings["pipeline_mode"] = self.pipeline_var.get()

    def update_view(self):
        if self.app.current_view == self and not self.up_to_date:
            self.up_to_date = True

            df = self.app.manager.current_df

            if self.app.manager.current_df is None:
                self.content_frame.pack_forget()
                self.footer_frame.pack_forget()
                self.history.pack_forget()
                self.no_dataset_frame.pack(pady=5)
                return

            self.no_dataset_frame.pack_forget()
            self.content_frame.pack(pady=20, padx=20, fill="both")
            self.footer_frame.pack(pady=20)
            self.history.pack(fill="both", expand=True)

            self.history.render_history()

            if self.current_columns.equals(df.columns):
                return

            self.current_columns = df.columns.copy()
            self.cat_columns = infer_column_types(self.app.manager.current_df)["categorical"]
            self.cat_column_rates = {"MAR": {},
                                     "NMAR": {}}

            self.update_settings_panel()
            self.update_categories_settings_panel()
            self.update_columns_panel()
            self.update_general_settings_panel()

    def on_update(self):
        self.up_to_date = False
        self.update_view()

    def create_settings_panel(self, parent):
        panel = ctk.CTkFrame(parent, corner_radius=10)
        panel.grid(
            row=0,
            column=0,
            padx=(0, 3),
            pady=0,
            sticky="nsew"
        )

        ctk.CTkLabel(
            panel,
            text="Missingness mechanism",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        for mechanism, description in [
            ("MCAR", "Missing Completely at Random"),
            ("MAR", "Missing at Random"),
            ("NMAR", "Missing Not at Random")
        ]:
            option = ctk.CTkFrame(panel, fg_color="transparent")
            option.pack(fill="x", padx=10, pady=4)

            option.grid_columnconfigure(0, weight=0)
            option.grid_columnconfigure(1, weight=1)
            option.grid_columnconfigure(2, weight=0)
            option.grid_rowconfigure(0, weight=1)
            option.grid_rowconfigure(1, weight=0)

            ctk.CTkRadioButton(
                option,
                text=mechanism,
                variable=self.selected_mechanism,
                value=mechanism,
                command=lambda: (
                    self.on_mechanism_changed(),
                    self.update_categories_settings_panel()
                )
            ).grid(row=0, column=0, sticky="w")

            ctk.CTkLabel(
                option,
                text=description,
                text_color="gray",
                font=ctk.CTkFont(size=11)
            ).grid(
                row=0,
                column=1,
                sticky="w",
                padx=(10, 0)
            )

            ctk.CTkCheckBox(
                option,
                variable=self.methods_active[mechanism],
                text="",
                command=self.on_mechanism_active_change
            ).grid(
                row=0,
                column=2,
                sticky="e"
            )

        ctk.CTkFrame(
            panel,
            height=2,
            fg_color=("gray80", "gray25")
        ).pack(fill="x", padx=15, pady=15)

        ctk.CTkLabel(
            panel,
            text="Parameters",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        parameters_frame = ctk.CTkFrame(
            panel,
            height=120,
            fg_color="transparent"
        )
        parameters_frame.pack(
            fill="x",
            padx=15,
            pady=(0, 15)
        )

        parameters_frame.pack_propagate(False)

        self.parameters_label = ctk.CTkLabel(
            parameters_frame,
            text="MCAR missingness rate",
            wraplength=450,
            justify="left"
        )
        self.parameters_label.pack(
            anchor="w",
            pady=(15, 5)
        )

        mcar_frame = ctk.CTkFrame(parameters_frame, fg_color="transparent")

        self.mcar_rate_label = ctk.CTkLabel(
            mcar_frame,
            text=f"{int(self.mcar_missingness_rate_var.get())}%"
        )
        self.mcar_rate_label.pack(anchor="w", padx=15)

        self.mcar_rate_slider = ctk.CTkSlider(
            mcar_frame,
            from_=1,
            to=100,
            number_of_steps=99,
            variable=self.mcar_missingness_rate_var,
            command=lambda value, label=self.mcar_rate_label: self.on_rate_changed(value, label),
        )
        self.mcar_rate_slider.pack(fill="x", padx=15, pady=(5, 10))

        self.parameter_frames["MCAR"] = mcar_frame

        mar_frame = ctk.CTkFrame(parameters_frame, fg_color="transparent")
        mar_frame.grid_propagate(False)
        mar_frame.columnconfigure(0, weight=0)
        mar_frame.columnconfigure(1, weight=0)
        mar_frame.columnconfigure(2, weight=0)
        mar_frame.columnconfigure(3, weight=1)

        mar_predictor_frame = ctk.CTkFrame(mar_frame, fg_color="transparent")
        mar_predictor_frame.grid(row=0, column=0, pady=5, sticky="nw")

        ctk.CTkLabel(mar_predictor_frame, text="Predictor:").pack(anchor="nw")

        self.mar_predictor_combobox = ctk.CTkComboBox(
            mar_predictor_frame,
            width=200,
            variable=self.mar_predictor_var,
            values=self.current_columns,
            command=lambda choice: self.update_categories_settings_panel(),
            state="readonly"
        )
        self.mar_predictor_combobox.pack(anchor="nw", pady=(0, 5))

        mar_rate_frame = ctk.CTkFrame(mar_frame, fg_color="transparent")
        mar_rate_frame.grid(row=0, column=1, pady=5, sticky="nw")

        self.mar_rate_label = ctk.CTkLabel(
            mar_rate_frame,
            text=f"Base rate: {self.base_rates['MAR'].get()}%"
        )
        self.mar_rate_label.pack(anchor="nw")

        self.mar_rate_slider = ctk.CTkSlider(
            mar_rate_frame,
            from_=1,
            to=100,
            number_of_steps=99,
            variable=self.base_rates["MAR"],
            command=lambda value, label=self.mar_rate_label: self.on_rate_changed(value, label,"Base rate: "),
        )
        self.mar_rate_slider.pack(fill="x", anchor="nw", pady=5)

        mar_strength_frame = ctk.CTkFrame(mar_frame, fg_color="transparent")
        mar_strength_frame.grid(row=0, column=2, pady=5, sticky="nw")

        self.mar_strength_label = ctk.CTkLabel(
            mar_strength_frame,
            text=f"Strength: {self.strengths['MAR'].get()}%"
        )
        self.mar_strength_label.pack(anchor="nw")

        self.mar_strength_slider = ctk.CTkSlider(
            mar_strength_frame,
            from_=1,
            to=100,
            number_of_steps=99,
            variable=self.strengths["MAR"],
            command=lambda value, label=self.mar_strength_label: self.on_rate_changed(value, label, "Strength: "),
        )
        self.mar_strength_slider.pack(fill="x", anchor="nw", pady=5)

        self.parameter_frames["MAR"] = mar_frame

        nmar_frame = ctk.CTkFrame(parameters_frame, fg_color="transparent")
        nmar_frame.grid_propagate(False)
        nmar_frame.columnconfigure(0, weight=0)
        nmar_frame.columnconfigure(1, weight=0)
        nmar_frame.columnconfigure(2, weight=1)

        nmar_rate_frame = ctk.CTkFrame(nmar_frame, fg_color="transparent")
        nmar_rate_frame.grid(row=0, column=0, pady=5)

        self.nmar_rate_label = ctk.CTkLabel(
            nmar_rate_frame,
            text=f"Base rate: {self.base_rates['NMAR'].get()}%"
        )
        self.nmar_rate_label.pack(anchor="nw")

        self.nmar_rate_slider = ctk.CTkSlider(
            nmar_rate_frame,
            from_=1,
            to=100,
            number_of_steps=99,
            variable=self.base_rates["NMAR"],
            command=lambda value, label=self.nmar_rate_label: self.on_rate_changed(value, label, "Base rate: "),
        )
        self.nmar_rate_slider.pack(fill="x", anchor="nw", pady=5)

        nmar_strength_frame = ctk.CTkFrame(nmar_frame, fg_color="transparent")
        nmar_strength_frame.grid(row=0, column=1, pady=5)

        self.nmar_strength_label = ctk.CTkLabel(
            nmar_strength_frame,
            text=f"Strength: {self.strengths['NMAR'].get()}%"
        )
        self.nmar_strength_label.pack(anchor="nw")

        self.nmar_strength_slider = ctk.CTkSlider(
            nmar_strength_frame,
            from_=1,
            to=100,
            number_of_steps=99,
            variable=self.strengths["NMAR"],
            command=lambda value, label=self.nmar_strength_label: self.on_rate_changed(value, label,"Strength: "),
        )
        self.nmar_strength_slider.pack(fill="x", anchor="nw", pady=5)

        self.parameter_frames["NMAR"] = nmar_frame

        mechanism = self.selected_mechanism.get()

        descriptions = {
            "MCAR": "MCAR missingness rate",
            "MAR": "Configure predictor columns and dependencies",
            "NMAR": "Configure dependencies on the missing values themselves"
        }

        self.parameters_label.configure(
            text=descriptions[mechanism]
        )

        for frame in self.parameter_frames.values():
            frame.pack_forget()

        self.parameter_frames[mechanism].pack(fill="x")

    def create_columns_panel(self, parent):
        panel = ctk.CTkFrame(parent, corner_radius=10)
        panel.grid(
            row=0,
            column=1,
            padx=(3, 0),
            pady=0,
            sticky="nsew"
        )

        ctk.CTkLabel(
            panel,
            text="Target columns",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            panel,
            text="Select columns in which to simulate missing values.",
            text_color="gray",
            wraplength=300,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 10))

        column_button_frame = ctk.CTkFrame(panel, fg_color="transparent")
        column_button_frame.pack(anchor="w", padx=15, pady=(0, 10))

        ctk.CTkButton(
            column_button_frame,
            text="Select All",
            command=lambda: (
                self.set_all_columns(True),
                self.update_categories_settings_panel()
            )
        ).grid(row=0,column=0,sticky="w",padx=5)

        ctk.CTkButton(
            column_button_frame,
            text="Clear All",
            command = lambda: (
                self.set_all_columns(False),
                self.update_categories_settings_panel()
            )
        ).grid(row=0, column=1, sticky="w", padx=5)

        self.columns_frame = ctk.CTkScrollableFrame(
            panel,
            fg_color="transparent"
        )
        self.columns_frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 10)
        )

        self.create_columns()

    def set_all_columns(self, value):
        for column in self.column_vars[self.selected_mechanism.get()].values():
            column.set(value)

    def create_general_settings_panel(self, parent):
        panel = ctk.CTkFrame(parent, corner_radius=10, height=200)
        panel.grid(
            row=2,
            column=0,
            columnspan=2,
            pady=6,
            sticky="nsew"
        )
        panel.grid_propagate(False)

        panel.grid_columnconfigure(0, weight=2, minsize=230)
        panel.grid_columnconfigure(1, weight=1)
        panel.grid_columnconfigure(2, weight=2)
        panel.grid_rowconfigure(0, weight=1)

        self.method_order_panel = ctk.CTkFrame(
            panel,
            fg_color="transparent",
            height=320,
            width=300
        )
        self.method_order_panel.grid_propagate(False)
        self.method_order_panel.grid(row=0, column=0,sticky="new", padx=(20, 10), pady=15)

        self.seed_panel = ctk.CTkFrame(
            panel,
            fg_color="transparent",
            height=320,
            width=300
        )
        self.seed_panel.grid_propagate(False)
        self.seed_panel.grid(row=0, column=1,sticky="new", padx=10, pady=15)

        self.pipeline_mode_panel = ctk.CTkFrame(
            panel,
            fg_color="transparent",
            height=320,
            width=300
        )
        self.pipeline_mode_panel.grid_propagate(False)
        self.pipeline_mode_panel.grid(row=0, column=2,sticky="new", padx=(10, 20), pady=15)

        self.create_pipeline_mode_panel()
        self.update_general_settings_panel()

    def create_categories_settings_panel(self, parent):
        self.categories_settings_panel = ctk.CTkScrollableFrame(parent, corner_radius=10, height=400)
        self.update_categories_settings_panel()

    def create_footer(self):
        footer = self.footer_frame

        ctk.CTkButton(
            footer,
            text="Reset Settings",
            command=self.reset_settings
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            footer,
            text="Simulate missingness",
            command=self.simulate_missingness
        ).pack(side="left", padx=5)

    def update_settings_panel(self):
        if self.mar_predictor_var.get() == "":
            self.mar_predictor_var.set(self.current_columns[0])
        self.mar_predictor_combobox.configure(values=self.current_columns)

    def update_columns_panel(self):
        for mechanism in self.column_vars.keys():
            self.column_vars[mechanism].clear()
            for column in self.current_columns:
                self.column_vars[mechanism][column] = ctk.BooleanVar(value=False)

        self.create_columns()

    def update_categories_settings_panel(self):
        if self.selected_mechanism.get() not in ("MAR", "NMAR"):
            self.categories_settings_panel.grid_forget()
            self.prev_mechanism = self.selected_mechanism.get()
            return

        if self.selected_mechanism.get() == "MAR":

            predictor = self.mar_predictor_var.get()

            if predictor in self.cat_columns:
                columns = [predictor]
            else:
                columns = []

        elif self.selected_mechanism.get() == "NMAR":

            columns = [
                col
                for col, var in self.column_vars["NMAR"].items()
                if var.get() and col in self.cat_columns
            ]

        if self.prev_cat_cols == columns and self.prev_mechanism == self.selected_mechanism.get():
            return

        self.prev_cat_cols = columns
        self.prev_mechanism = self.selected_mechanism.get()

        if len(columns) == 0:
            self.categories_settings_panel.grid_forget()
            return

        self.categories_settings_panel.grid(
            row=1,
            column=0,
            columnspan=2,
            pady=(6, 0),
            sticky="nsew"
        )

        for widget in self.categories_settings_panel.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.categories_settings_panel,
            text="Categories missingness rates",
            font=('Arial', 22, 'bold'),
        ).pack(anchor="n")

        def set_all_category_rates(mechanism, col, value, labels):
            for var in self.cat_column_rates[mechanism][col].values():
                var.set(value)
            for label in labels:
                label.configure(text=f"{value}%")

        def create_category_section(
                parent,
                mechanism,
                column_name,
                cats
        ):
            section = ctk.CTkFrame(parent)

            section.pack(
                fill="x",
                padx=5,
                pady=5
            )

            ctk.CTkLabel(
                section,
                text=column_name,
                font=("Arial", 16, "bold")
            ).pack(anchor="w")

            preset_frame = ctk.CTkFrame(
                section,
                fg_color="transparent"
            )

            preset_frame.pack(
                fill="x",
                pady=(5, 10)
            )

            labels = []

            for category in cats:
                row = ctk.CTkFrame(
                    section,
                    fg_color="transparent"
                )

                row.pack(fill="x")

                ctk.CTkLabel(
                    row,
                    text=str(category),
                    width=150
                ).pack(side="left")

                value_label = ctk.CTkLabel(
                    row,
                    text=f"{int(self.cat_column_rates[self.selected_mechanism.get()][column][category].get())}%"
                )

                labels.append(value_label)

                slider = ctk.CTkSlider(
                    row,
                    from_=0,
                    to=100,
                    variable=self.cat_column_rates[self.selected_mechanism.get()][column][category],
                    command=lambda value,
                                   label=value_label:
                    label.configure(
                        text=f"{value:.0f}%"
                    )
                )

                slider.pack(side="left")
                value_label.pack(side="left")

            for preset in [0, 10, 25, 50, 75]:
                ctk.CTkButton(
                    preset_frame,
                    text=f"{preset}%",
                    width=50,
                    command=lambda
                        p=preset,
                        mech=mechanism,
                        col=column_name:
                    set_all_category_rates(
                        mech,
                        col,
                        p,
                        labels
                    )
                ).pack(side="left", padx=2)

        for column in columns:
            categories = sorted(
                self.app.manager.current_df[column]
                .dropna()
                .unique()
            )

            if column in self.cat_column_rates[self.selected_mechanism.get()].keys():
                if categories != self.cat_column_rates[self.selected_mechanism.get()][column].keys():
                    self.cat_column_rates[self.selected_mechanism.get()].pop(column, None)

            if column not in self.cat_column_rates[self.selected_mechanism.get()].keys():
                self.cat_column_rates[self.selected_mechanism.get()][column] = {
                    category : ctk.DoubleVar(value=0.0) for category in categories
                }

            create_category_section(self.categories_settings_panel, self.selected_mechanism.get(), column, categories)

    def create_columns(self):
        for widget in self.columns_frame.winfo_children():
            widget.destroy()

        self.column_checkboxes.clear()

        for column in self.current_columns:
            checkbox = ctk.CTkCheckBox(
                self.columns_frame,
                text=str(column),
                variable=self.column_vars[self.selected_mechanism.get()][column],
                command=self.update_categories_settings_panel
            )
            checkbox.pack(anchor="w", padx=5, pady=5)
            self.column_checkboxes[column] = checkbox

    def update_general_settings_panel(self):
        self.update_method_order_panel()
        self.update_seed_panel()

    def update_method_order_panel(self):
        for widget in self.method_order_panel.winfo_children():
            widget.destroy()

        ctk.CTkLabel(self.method_order_panel, text="Method order:", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(5, 0))

        methods = ["MCAR", "MAR", "NMAR"]
        active_methods = [(idx, method) for idx, (method, var) in enumerate(self.methods_active.items()) if var.get()]
        for i in range(len(methods)):
            if i < len(active_methods):
                frame = ctk.CTkFrame(
                    self.method_order_panel,
                    fg_color="transparent",
                    height=40,
                    width=200
                )
                frame.pack(
                    fill="x",
                    expand=False,
                    pady=2
                )
                frame.pack_propagate(False)
                ctk.CTkLabel(frame, text=str(i+1)+". ").pack(side="left")
                ctk.CTkComboBox(
                    frame,
                    variable=self.method_order[i],
                    values=[method_name for _, method_name in active_methods],
                    state="readonly",
                    width=180,
                    command=
                    lambda method, idx = i: self.update_method_order(idx)
                ).pack(anchor="w", side="left", padx=5, pady=5)
                index = active_methods[i][0]
                self.method_order[i].set(methods[index])
            else:
                self.method_order[i].set("None")

    def update_method_order(self, index):
        if len([method for method, var in self.methods_active.items() if var.get()]) == 1:
            return

        active_methods = [var.get() for var in self.method_order if var.get() != "None"]
        if len(active_methods) == len(set(active_methods)):
            return

        changed_var = self.method_order[index].get()
        old_var = [i for i, var in enumerate(self.method_order) if i != index and var.get() == changed_var][0]
        self.method_order[old_var].set(next(iter(set([method for method, var in self.methods_active.items() if var.get()]) -
                                       set([method.get() for method in self.method_order]))))

    def update_seed_panel(self):
        for widget in self.seed_panel.winfo_children():
            widget.destroy()

        ctk.CTkLabel(self.seed_panel, text="RNG Seed Selection:", font=("Arial", 14, "bold")).pack(anchor="w", padx=10,
                                                                                              pady=5)

        selection_row = ctk.CTkFrame(self.seed_panel, fg_color="transparent")
        selection_row.pack(fill="x", padx=10, pady=5)

        self.seed_combobox = ctk.CTkComboBox(
            selection_row,
            variable=self.seed_var,
            values=self.seeds,
            state="readonly",
            width=200
        )
        self.seed_combobox.pack(side="left", padx=(0, 10))

        btn_delete = ctk.CTkButton(
            selection_row,
            text="Delete",
            fg_color="#D32F2F", hover_color="#B71C1C",
            width=80,
            command=self.delete_current_seed
        )
        btn_delete.pack(side="left")

        action_row = ctk.CTkFrame(self.seed_panel, fg_color="transparent")
        action_row.pack(fill="x", padx=10, pady=10)

        btn_random = ctk.CTkButton(
            action_row,
            text="Generate Random",
            width=150,
            command=self.generate_random_seed
        )
        btn_random.pack(side="left", padx=(0, 10))

        self.new_seed_entry = ctk.CTkEntry(action_row, placeholder_text="Enter manual seed...", width=150)
        self.new_seed_entry.pack(side="left", padx=(0, 10))

        btn_add = ctk.CTkButton(
            action_row,
            text="➕ Add",
            width=80,
            command=self.add_manual_seed
        )
        btn_add.pack(side="left")

        always_random_row = ctk.CTkFrame(self.seed_panel, fg_color="transparent")
        always_random_row.pack(fill="x", padx=10, pady=10)

        ctk.CTkCheckBox(
            always_random_row,
            variable=self.always_random_var,
            text="Always Random Seed"
        ).pack(side="left")

    def create_pipeline_mode_panel(self):
        pipeline_combobox = ctk.CTkComboBox(
            self.pipeline_mode_panel,
            variable=self.pipeline_var,
            values=["Sequential", "Independent"],
            state="readonly",
            width=200,
            command=self.on_pipeline_change
        )
        pipeline_combobox.pack(pady=5, anchor="nw")

        pipeline_desc_frame = ctk.CTkFrame(
            self.pipeline_mode_panel,
            height=80,
            fg_color="transparent"
        )

        pipeline_desc_frame.pack(
            fill="x",
            pady=5
        )

        pipeline_desc_frame.pack_propagate(False)

        self.pipeline_desc = ctk.CTkLabel(
            pipeline_desc_frame,
            wraplength=350,
            text_color="gray",
            justify="left",
            anchor="nw"
        )
        self.pipeline_desc.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=5
        )
        self.on_pipeline_change(self.pipeline_var.get())

    def generate_random_seed(self):
        random_seed = str(random.randint(0, 999999))
        if random_seed not in self.seeds:
            self.seeds.append(random_seed)
            self.seed_combobox.configure(values=self.seeds)

        self.seed_var.set(random_seed)

    def add_manual_seed(self):
        new_seed = self.new_seed_entry.get().strip()

        if new_seed and new_seed.isdigit():
            if new_seed not in self.seeds:
                self.seeds.append(new_seed)
                self.seed_combobox.configure(values=self.seeds)

            self.seed_var.set(new_seed)

        self.new_seed_entry.delete(0, "end")

    def delete_current_seed(self):
        current_seed = self.seed_var.get()

        if len(self.seeds) > 0:
            self.seeds.remove(current_seed)
            self.seed_combobox.configure(values=self.seeds)
            if len(self.seeds) > 0:
                self.seed_var.set(self.seeds[0])
            else:
                self.seed_var.set("")

    def reset_columns(self):
        for col_vars in self.column_vars.values():
            for var in col_vars.values():
                var.set(False)


    def on_mechanism_active_change(self):
        self.update_method_order_panel()

    def on_mechanism_changed(self):
        mechanism = self.selected_mechanism.get()

        descriptions = {
            "MCAR": "MCAR missingness rate",
            "MAR": "Configure predictor columns and dependencies",
            "NMAR": "Configure dependencies on the missing values themselves"
        }

        self.parameters_label.configure(
            text=descriptions[mechanism]
        )

        for frame in self.parameter_frames.values():
            frame.pack_forget()

        self.parameter_frames[mechanism].pack(fill="x")

        for column in self.current_columns:
            self.column_checkboxes[column].configure(variable=self.column_vars[mechanism][column])


    def on_rate_changed(self, value, rate_label, preceding = ""):
        rate_label.configure(
            text=f"{preceding}{value:.0f}%"
        )

    def on_pipeline_change(self, pipeline):
        if pipeline == "Sequential":
            self.pipeline_desc.configure(text="Missingness methods are applied sequentially, "
                 "each to the result of the previous method.")
        elif pipeline == "Independent":
            self.pipeline_desc.configure(text="Each missingness method is applied independently. The results are then "
                 "combined, meaning the order of methods does not matter.")

    def reset_settings(self):
        self.selected_mechanism.set("MCAR")
        self.mcar_missingness_rate_var.set(20.0)

        for active_method in self.methods_active.values():
            active_method.set(False)

        self.mar_predictor_var.set(self.current_columns[0] if len(self.current_columns) > 0 else "")

        for var in self.base_rates.values():
            var.set(10.0)

        for var in self.strengths.values():
            var.set(10.0)

        self.mar_rate_label.configure(text = f"Base rate: {self.base_rates['MAR'].get()}%")
        self.mar_strength_label.configure(text = f"Strength: {self.strengths['MAR'].get()}%")
        self.nmar_rate_label.configure(text = f"Base rate: {self.base_rates['NMAR'].get()}%")
        self.nmar_strength_label.configure(text = f"Strength: {self.strengths['NMAR'].get()}%")

        for cols in self.cat_column_rates.values():
            cols.clear()

        self.prev_cat_cols.clear()

        self.method_order[0].set("MCAR")
        self.method_order[1].set("MAR")
        self.method_order[2].set("NMAR")

        if len(self.seeds) > 0:
            self.seed_var.set(self.seeds[0])
        else:
            self.seed_var.set("")

        self.always_random_var.set(False)

        self.pipeline_var.set("Sequential")

        self.on_mechanism_changed()
        self.on_rate_changed(20.0, self.mcar_rate_label)
        self.reset_columns()
        self.update_categories_settings_panel()

    def simulate_missingness(self):
        df = self.app.manager.current_df

        if df is None:
            return

        active_methods = {
            method: var.get()
            for method, var in self.methods_active.items()
        }

        method_order = [
            var.get()
            for var in self.method_order
        ]

        method_columns = {
            method: [
                column
                for column, var in columns.items()
                if var.get()
            ]
            for method, columns in self.column_vars.items()
        }

        categorical_column_rates = {
            method: {
                column: {
                    category: var.get() / 100.0
                    for category, var in categories.items()
                }
                for column, categories in columns.items()
            }
            for method, columns in self.cat_column_rates.items()
        }

        mcar_missingness_rate = self.mcar_missingness_rate_var.get() / 100.0

        base_rates = {
            method: var.get() / 100.0
            for method, var in self.base_rates.items()
        }

        strengths = {
            method: var.get() / 100.0
            for method, var in self.strengths.items()
        }

        mar_predictor = self.mar_predictor_var.get()

        always_random_seed = self.always_random_var.get()
        rng_seed = self.seed_var.get().strip()

        if not always_random_seed:
            if not rng_seed or rng_seed == "":
                rng_seed = None
            try:
                rng_seed = int(rng_seed)
            except (ValueError, TypeError):
                rng_seed = None
        else:
            rng_seed = None

        pipeline_mode = self.pipeline_var.get()

        valid_method = False

        for method in method_order:
            if not active_methods.get(method, False):
                continue

            targets = method_columns.get(method, [])
            if len(targets) == 0:
                continue

            if method == "MCAR":
                valid_method = (
                        mcar_missingness_rate > 0
                        and len(targets) > 0
                )

            elif method == "MAR":
                targets = [
                    col for col in targets
                    if col != mar_predictor
                ]

                if not targets:
                    continue

                if pd.api.types.is_numeric_dtype(df[mar_predictor]):
                    valid_method = base_rates["MAR"] > 0 or strengths["MAR"] > 0
                else:
                    predictor_rates = (
                        categorical_column_rates
                        .get("MAR", {})
                        .get(mar_predictor, {})
                    )
                    valid_method = any(
                        rate > 0 for rate in predictor_rates.values()
                    )

            elif method == "NMAR":
                rates = base_rates["MAR"] > 0 or strengths["MAR"] > 0
                for target in targets:
                    if pd.api.types.is_numeric_dtype(df[target]):
                        if rates:
                            valid_method = True
                            break

                    category_rates = (
                        categorical_column_rates
                        .get("NMAR", {})
                        .get(target, {})
                    )

                    if any(rate > 0 for rate in category_rates.values()):
                        valid_method = True
                        break

            if valid_method:
                break

        if not valid_method:
            return

        self.app.manager.apply_missingness_pipeline(
            active_methods=active_methods,
            mcar_missingness_rate=mcar_missingness_rate,
            method_columns=method_columns,
            categorical_column_rates=categorical_column_rates,
            method_order=method_order,
            mar_predictor=mar_predictor,
            base_rates=base_rates,
            strengths=strengths,
            rng_seed=rng_seed,
            always_random_seed=always_random_seed,
            pipeline_mode=pipeline_mode,
        )

        self.app.manager.save_app_data()



