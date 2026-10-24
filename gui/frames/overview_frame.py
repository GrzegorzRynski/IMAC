import customtkinter as ctk
from tkinter import ttk

import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap

from correlation_functions import cramers_v, correlation_ratio
from gui.components.history_view import HistoryView
from init_analitics.init_analytics import report

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class OverviewView(ctk.CTkScrollableFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.page_size = 1000
        self.current_page = 0
        self.filtered_df = None

        self.up_to_date = {
            "main" : False,
            "tables" : False,
            "moreinfo" : False,
            "charts" : False,
            "correlation" : False,
            "missing" : False,
            "history" : False
        }

        self.df = None
        self.report = None

        # --- TITLE ---
        title = ctk.CTkLabel(self, text="Dataset Overview", font=("Arial", 24, "bold"))
        title.pack(pady=(10, 20))

        # --- NAME DISPLAY ---
        self.name_label = ctk.CTkLabel(self, text="No Dataset Selected", font=("Arial", 22, "bold"), wraplength=1200)
        self.name_label.pack(pady=10)

        # --- INFO BAR ---
        self.info_label = ctk.CTkLabel(self, text="", font=("Arial", 16))
        self.info_label.pack(pady=10)

        self.tabs = ctk.CTkTabview(self, fg_color="transparent", command=self.update_view)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)

        tables_tab = self.tabs.add("Tables")
        tables_tab.configure(fg_color="transparent")

        moreinfo_tab = self.tabs.add("More Info")

        charts_tab = self.tabs.add("Charts")
        charts_tab.configure(fg_color="transparent")

        correlation_tab = self.tabs.add("Correlation")
        correlation_tab.configure(fg_color="transparent")

        missing_tab = self.tabs.add("Missing Patterns")
        missing_tab.configure(fg_color="transparent")

        self.history = HistoryView(self, self.app.manager.df_history, self)

        # --- SEARCH BAR ---
        search_frame = ctk.CTkFrame(tables_tab, fg_color="transparent")
        search_frame.pack(fill="x", pady=(0, 10), padx=(20, 0))

        search_label = ctk.CTkLabel(search_frame, text="Search:", font=("Arial", 14))
        search_label.pack(side="left", padx=(0, 10))

        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *args: self.apply_search_filter())

        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var, width=300)
        search_entry.pack(side="left")

        # --- MAIN SPLIT FRAME ---
        split_frame = ctk.CTkFrame(tables_tab, fg_color="transparent")
        split_frame.pack(fill="both", expand=True, padx=10, pady=10)

        split_frame.grid_columnconfigure(0, weight=3, minsize=800)
        split_frame.grid_columnconfigure(1, weight=0, minsize=400)
        split_frame.grid_rowconfigure(0, weight=1)

        # --- TABLE AREA ---
        self.table_container = ctk.CTkFrame(split_frame)
        self.table_container.grid(row=0, column=0, sticky="nswe", padx=10)

        # Scrollbars
        self.table_scroll_y = ctk.CTkScrollbar(self.table_container, orientation="vertical")
        self.table_scroll_y.pack(side="right", fill="y")

        self.table_scroll_x = ctk.CTkScrollbar(self.table_container, orientation="horizontal")
        self.table_scroll_x.pack(side="bottom", fill="x")

        # Treeview
        style = ttk.Style()
        style.theme_use("default")

        style.configure(
            "Treeview",
            background="#2b2b2b",
            foreground="white",
            fieldbackground="#2b2b2b",
            rowheight=25,
            bordercolor="#444444",
            borderwidth=0
        )

        style.configure(
            "Treeview.Heading",
            background="#1f1f1f",
            foreground="white",
            relief="flat"
        )

        style.map(
            "Treeview",
            background=[("selected", "#3a7bd5")],
            foreground=[("selected", "white")]
        )

        self.table = ttk.Treeview(
            self.table_container,
            show="headings",
            yscrollcommand=self.table_scroll_y.set,
            xscrollcommand=self.table_scroll_x.set
        )
        self.table.pack(fill="both", expand=True)

        self.table.tag_configure("missing_row", background="#662222")

        self.table_scroll_y.configure(command=self.table.yview)
        self.table_scroll_x.configure(command=self.table.xview)

        pagination_frame = ctk.CTkFrame(self.table_container, fg_color="transparent")
        pagination_frame.pack(fill="x", pady=10)

        pagination_frame.grid_columnconfigure(0, weight=1)
        pagination_frame.grid_columnconfigure(1, weight=1)
        pagination_frame.grid_columnconfigure(2, weight=1)
        pagination_frame.grid_columnconfigure(3, weight=0)
        pagination_frame.grid_columnconfigure(4, weight=0)

        self.prev_btn = ctk.CTkButton(
            pagination_frame, text="Previous", width=100,
            command=self.prev_page
        )
        self.prev_btn.grid(row=0, column=0, pady=5)

        self.page_label = ctk.CTkLabel(
            pagination_frame, text="Page 1 / 1", font=("Arial", 14)
        )
        self.page_label.grid(row=0, column=1, pady=5)

        self.next_btn = ctk.CTkButton(
            pagination_frame, text="Next", width=100,
            command=self.next_page
        )
        self.next_btn.grid(row=0, column=2, pady=5)

        self.goto_var = ctk.StringVar()

        goto_entry = ctk.CTkEntry(
            pagination_frame,
            textvariable=self.goto_var,
            width=80,
            placeholder_text="Page"
        )
        goto_entry.grid(row=0, column=3, padx=10)

        goto_btn = ctk.CTkButton(
            pagination_frame,
            text="Go",
            width=60,
            command=self.goto_page
        )
        goto_btn.grid(row=0, column=4, padx=5)

        # --- STATS AREA ---
        self.stats_frame = ctk.CTkFrame(split_frame)
        self.stats_frame.grid(row=0, column=1, sticky="nswe", padx=10)

        # Scrollbar
        self.stats_scroll_y = ctk.CTkScrollbar(self.stats_frame, orientation="vertical")
        self.stats_scroll_y.pack(side="right", fill="y")

        # Treeview for stats
        self.stats_table = ttk.Treeview(
            self.stats_frame,
            show="headings",
            yscrollcommand=self.stats_scroll_y.set,
            height=20
        )
        self.stats_table.pack(fill="both", expand=False)

        self.stats_scroll_y.configure(command=self.stats_table.yview)

        buttons_frame = ctk.CTkFrame(tables_tab, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=10)

        center_frame = ctk.CTkFrame(buttons_frame, fg_color="transparent")
        center_frame.pack(anchor="center")

        mark_as_missing_btn = ctk.CTkButton(
            center_frame,
            text="Mark unusual as missing",
            command=lambda
                unusual_tokens = [
                    "",
                    " ",
                    "NA",
                    "N/A",
                    "NULL",
                    "null",
                    "?",
                    "-"
                ]:
            self.app.manager.mark_unusual_as_missing(self.report, unusual_tokens),
            fg_color="#3a7bd5",
            hover_color="#2f5fa8"
        )
        mark_as_missing_btn.pack(side="left", padx=5)

        delete_rows_btn = ctk.CTkButton(
            center_frame,
            text="Delete rows with unusual",
            command=lambda
                unusual_tokens=[
                    "",
                    " ",
                    "NA",
                    "N/A",
                    "NULL",
                    "null",
                    "?",
                    "-"
                ]:
            self.app.manager.delete_unusual_rows(self.report, unusual_tokens),
            fg_color="#3a7bd5",
            hover_color="#2f5fa8"
        )
        delete_rows_btn.pack(side="left", padx=5)

        reset_btn = ctk.CTkButton(
            center_frame,
            text="Reset Tables",
            command=self.reset_tables,
            fg_color="#3a7bd5",
            hover_color="#2f5fa8"
        )
        reset_btn.pack(side="left", padx=5)

        # Register auto-update
        self.app.manager.register_update_callback(self.on_update)

        # ---------------------- MORE INFO ---------------------------------------------------------

        self.moreinfo_frame = ctk.CTkScrollableFrame(moreinfo_tab, fg_color="transparent", height=500)
        self.moreinfo_frame.pack(fill="both", expand=True, padx=50, pady=50)

        # ---------------------- CHARTS TAB ---------------------------------------------------------

        charts_container = ctk.CTkFrame(charts_tab, fg_color="transparent")
        charts_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Column selector
        selector_label = ctk.CTkLabel(
            charts_container,
            text="Select column:",
            font=("Arial", 16)
        )
        selector_label.pack(anchor="w", pady=(0, 5))

        self.chart_column_var = ctk.StringVar()

        self.chart_selector = ctk.CTkComboBox(
            charts_container,
            variable=self.chart_column_var,
            values=[],
            width=300,
            state="readonly",
            command=self.update_charts
        )
        self.chart_selector.pack(anchor="w", pady=(0, 20))

        # Chart display area
        self.chart_frame = ctk.CTkFrame(charts_container, fg_color="transparent")
        self.chart_frame.pack(fill="both", expand=True)

        # ---------------------- CORRELATION TAB ---------------------------------------------------------

        correlation_container = ctk.CTkFrame(correlation_tab, fg_color="transparent")
        correlation_container.pack(fill="both", expand=True, padx=20, pady=20)

        self.corr_type_var = ctk.StringVar(value="Full")
        self.prev_corr_selection = ""

        corr_selector = ctk.CTkComboBox(
            correlation_container,
            variable=self.corr_type_var,
            state="readonly",
            values=["Full", "Numeric", "Categorical"],
            width=300,
            command=lambda _: self.update_correlation()
        )
        corr_selector.pack(anchor="w", padx=20, pady=(10, 5))

        self.correlation_frame = ctk.CTkFrame(correlation_container, fg_color="transparent")
        self.correlation_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # ---------------------- MISSING TAB ---------------------------------------------------------
        self.missing_frame = ctk.CTkFrame(missing_tab, fg_color="transparent")
        self.missing_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Initial update
        self.update_view()

    def sort_treeview(self, tree, col, reverse):
        """Sort a Treeview column."""
        data = [(tree.set(k, col), k) for k in tree.get_children("")]

        # Try numeric sort
        try:
            data.sort(key=lambda t: float(t[0]) if t[0] not in ("", None) else float("-inf"), reverse=reverse)
        except ValueError:
            # Fallback: string sort
            data.sort(key=lambda t: t[0], reverse=reverse)

        # Reinsert rows
        for index, (_, k) in enumerate(data):
            tree.move(k, "", index)

        # Toggle next sort direction
        tree.heading(col, command=lambda: self.sort_treeview(tree, col, not reverse))

    def load_page(self):
        """Load only the current page of the DataFrame into the table."""
        df = self.filtered_df if self.filtered_df is not None else self.app.manager.current_df
        if df is None:
            return

        # Clear table
        for row in self.table.get_children():
            self.table.delete(row)

        # Compute page boundaries
        start = self.current_page * self.page_size
        end = start + self.page_size
        page_df = df.iloc[start:end]

        # Insert rows
        for index, row in page_df.iterrows():
            values = [
                index + 1 if isinstance(index, int) else index
            ]

            has_missing = False

            for value in row.values:
                if pd.isna(value) or (
                        isinstance(value, str) and value.strip() == ""
                ):
                    values.append("-")
                    has_missing = True
                else:
                    values.append(value)

            if has_missing:
                self.table.insert(
                    "",
                    "end",
                    values=values,
                    tags=("missing_row",)
                )
            else:
                self.table.insert("", "end", values=values)

        # Update page label
        total_pages = max(1, (len(df) - 1) // self.page_size + 1)
        self.page_label.configure(text=f"Page {self.current_page + 1} / {total_pages}")

        # Enable/disable buttons
        self.prev_btn.configure(state="normal" if self.current_page > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.current_page < total_pages - 1 else "disabled")

    def next_page(self):
        df = self.filtered_df if self.filtered_df is not None else self.app.manager.current_df
        if df is None:
            return

        total_pages = max(1, (len(df) - 1) // self.page_size + 1)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.load_page()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_page()

    def goto_page(self):
        """Jump to a specific page number."""
        df = self.filtered_df if self.filtered_df is not None else self.app.manager.current_df
        if df is None:
            return

        try:
            page = int(self.goto_var.get()) - 1
        except ValueError:
            return

        total_pages = max(1, (len(df) - 1) // self.page_size + 1)

        if 0 <= page < total_pages:
            self.current_page = page
            self.load_page()

    def reset_tables(self):
        """Reset both tables to their original unsorted order."""
        df = self.app.manager.current_df
        if df is None:
            return

        self.search_var.set("")

        # Clear stats table
        for row in self.stats_table.get_children():
            self.stats_table.delete(row)

        # Reinsert original stats
        missing_df = self.report["missing"]
        types_dict = self.report["types"]

        for col in df.columns:
            dtype = (
                "Num" if col in types_dict["numeric"] else
                "Cat" if col in types_dict["categorical"] else
                "Text"
            )

            miss = int(missing_df.loc[col, "missing_count"])
            miss_pct = f"{missing_df.loc[col, 'missing_pct']:.2f}%"
            unusual = int(missing_df.loc[col, "unusual_token_count"])

            self.stats_table.insert("", "end", values=(col, dtype, miss, miss_pct, unusual))

        self.filtered_df = None
        self.current_page = 0
        self.load_page()

    def apply_search_filter(self):
        """Filter main table based on search bar input."""
        df = self.app.manager.current_df
        if df is None:
            return

        query = self.search_var.get().strip().lower()

        # Clear table
        for row in self.table.get_children():
            self.table.delete(row)

        if query == "":
            self.filtered_df = None
            self.current_page = 0
            self.load_page()
            return

        self.filtered_df = df[df.apply(lambda row: any(query in str(v).lower() for v in row.values), axis=1)]
        self.current_page = 0
        self.load_page()

    def on_update(self):
        for key, value in self.up_to_date.items():
            self.up_to_date[key] = False
        self.update_view()

    def update_view(self):

        if self.app.current_view == self:
            if not self.up_to_date["main"]:
                self.df = self.app.manager.current_df

                if self.df is None:
                    self.info_label.pack_forget()
                    self.tabs.pack_forget()
                    self.name_label.configure(text="No Dataset Loaded")
                    self.table["columns"] = []
                    self.stats_table["columns"] = []
                    return

                # --- NAME ---
                self.name_label.configure(text=f"Dataset: {self.app.manager.current_name}")

                # --- REPORT ---
                self.report = report(self.df)

                # --- INFO BAR ---
                missing_percent = self.df.isna().sum().sum() / self.df.size * 100
                self.info_label.pack(pady=10)
                self.info_label.configure(
                    text=f"Rows: {len(self.df)} | Columns: {len(self.df.columns)} | "
                         f"Missing: {missing_percent:.2f}%"
                )

                self.tabs.pack(fill="both", expand=True, padx=10, pady=10)
                self.up_to_date["main"] = True

            # --- TABS ---
            if self.tabs.get() == "Tables":
                if not self.up_to_date["tables"]:
                    self.update_tables(self.df, self.report)
                    self.up_to_date["tables"] = True

            if self.tabs.get() == "More Info":
                if not self.up_to_date["moreinfo"]:
                    self.update_more_info(self.report)
                    self.up_to_date["moreinfo"] = True

            if self.tabs.get() == "Charts":
                if not self.up_to_date["charts"]:
                    self.chart_selector.configure(values=list(self.df.columns))
                    self.update_charts()
                    self.up_to_date["charts"] = True

            if self.tabs.get() == "Correlation":
                if not self.up_to_date["correlation"]:
                    self.update_correlation()
                    self.up_to_date["correlation"] = True

            if self.tabs.get() == "Missing Patterns":
                if not self.up_to_date["missing"]:
                    self.update_missing_patterns(self.report)
                    self.up_to_date["missing"] = True

            # --- HISTORY ---
            if not self.up_to_date["history"]:
                self.history.pack(fill="both", expand=True)
                self.history.render_history()
                self.up_to_date["history"] = True

    def update_tables(self, df, df_report):
        missing_df = df_report["missing"]
        types_dict = df_report["types"]

        self.table_container.grid_forget()
        self.stats_frame.grid_forget()

        # Clear tables
        for row in self.table.get_children():
            self.table.delete(row)

        for row in self.stats_table.get_children():
            self.stats_table.delete(row)

        # --- MAIN DATA TABLE ---
        self.table["columns"] = ["Index"] + list(df.columns)

        for col in df.columns:
            self.table.heading(col, text=col)
            self.table.column(col, width=120, anchor="w", stretch=False)

        self.table.heading("Index", text="Index", command=lambda: self.sort_treeview(self.table, "Index", False))
        self.table.column("Index", width=60, anchor="w", stretch=False)

        for index, row in df.iterrows():
            values = list(row.values)

            if any(v is None or (isinstance(v, float) and pd.isna(v)) for v in values):
                self.table.insert("", "end", values=[index + 1] + list(row.values), tags=("missing_row",))
            else:
                self.table.insert("", "end", values=[index + 1] + list(row.values))

        for col in df.columns:
            self.table.heading(col, text=col, command=lambda c=col: self.sort_treeview(self.table, c, False))

        # --- STATS TABLE ---
        self.stats_table["columns"] = ("Column", "Type", "Missing", "Missing %", "Unusual")

        self.stats_table.column("Column", width=100, anchor="w", stretch=False)
        self.stats_table.column("Type", width=60, anchor="w", stretch=False)
        self.stats_table.column("Missing", width=60, anchor="center", stretch=False)
        self.stats_table.column("Missing %", width=80, anchor="center", stretch=False)
        self.stats_table.column("Unusual", width=80, anchor="center", stretch=False)

        for col in ("Column", "Type", "Missing", "Missing %", "Unusual"):
            self.stats_table.heading(col, text=col,
                                     command=lambda c=col: self.sort_treeview(self.stats_table, c, False))

        for col in df.columns:
            dtype = (
                "Num" if col in types_dict["numeric"] else
                "Cat" if col in types_dict["categorical"] else
                "Text"
            )

            miss = int(missing_df.loc[col, "missing_count"])
            miss_pct = f"{missing_df.loc[col, 'missing_pct']:.2f}%"
            unusual = int(missing_df.loc[col, "unusual_token_count"])

            self.stats_table.insert("", "end", values=(col, dtype, miss, miss_pct, unusual))

        self.table_container.grid(row=0, column=0, sticky="nswe", padx=10)
        self.stats_frame.grid(row=0, column=1, sticky="nswe", padx=10)

        self.current_page = 0
        self.filtered_df = None
        self.load_page()

    def update_more_info(self, df_report):
        # Clear previous content
        for widget in self.moreinfo_frame.winfo_children():
            widget.destroy()

        # --- Missing Summary ---
        missing_frame = ctk.CTkFrame(self.moreinfo_frame)
        missing_frame.pack(fill="x", pady=10, padx=10, ipadx=10)

        missing_df = df_report["missing"]

        # Total missing
        total_missing = int(missing_df["missing_count"].sum())
        total_pct = float(missing_df["missing_pct"].mean())

        total_label = ctk.CTkLabel(
            missing_frame,
            text=f"Total missing values: {total_missing} ({total_pct:.2f}%)",
            font=("Arial", 20, "bold")
        )
        total_label.pack(anchor="w", pady=10, padx=10)

        # --- TYPE SUMMARY ---
        types_frame = ctk.CTkFrame(self.moreinfo_frame)
        types_frame.pack(fill="x", pady=10, padx=10)

        types_dict = df_report["types"]

        type_title = ctk.CTkLabel(
            types_frame,
            text="Type Summary",
            font=("Arial", 20, "bold")
        )
        type_title.pack(anchor="w", pady=(0, 10), padx=10)

        # Counts
        num_count = len(types_dict["numeric"])
        cat_count = len(types_dict["categorical"])
        text_count = len(types_dict["text"])

        counts_label = ctk.CTkLabel(
            types_frame,
            text=f"Numeric: {num_count} | Categorical: {cat_count} | Text: {text_count}",
            font=("Arial", 16)
        )
        counts_label.pack(anchor="w", pady=5, padx=15)

        # Numeric columns
        if num_count > 0:
            num_label = ctk.CTkLabel(
                types_frame,
                text="Numeric Columns:",
                font=("Arial", 15, "bold")
            )
            num_label.pack(anchor="w", pady=(10, 2), padx=15)

            for col in types_dict["numeric"]:
                item = ctk.CTkLabel(types_frame, text=f"• {col}", font=("Arial", 14))
                item.pack(anchor="w", padx=20)

        # Categorical columns
        if cat_count > 0:
            cat_label = ctk.CTkLabel(
                types_frame,
                text="Categorical Columns:",
                font=("Arial", 15, "bold")
            )
            cat_label.pack(anchor="w", pady=(10, 2), padx=15)

            for col in types_dict["categorical"]:
                item = ctk.CTkLabel(types_frame, text=f"• {col}", font=("Arial", 14))
                item.pack(anchor="w", padx=20)

        # Text columns
        if text_count > 0:
            text_label = ctk.CTkLabel(
                types_frame,
                text="Text Columns:",
                font=("Arial", 15, "bold")
            )
            text_label.pack(anchor="w", pady=(10, 2), padx=15)

            for col in types_dict["text"]:
                item = ctk.CTkLabel(types_frame, text=f"• {col}", font=("Arial", 14))
                item.pack(anchor="w", padx=20)

        # --- Categorical Values ---
        unique_frame = ctk.CTkFrame(self.moreinfo_frame)
        unique_frame.pack(fill="x", pady=10, padx=10)

        unique_title = ctk.CTkLabel(
            unique_frame,
            text="Categorical Values",
            font=("Arial", 20, "bold")
        )
        unique_title.pack(anchor="w", pady=(0, 10), padx=10)

        df = self.app.manager.current_df
        types_dict = df_report["types"]

        categorical_cols = types_dict["categorical"]

        if len(categorical_cols) == 0:
            no_cat_label = ctk.CTkLabel(
                unique_frame,
                text="No categorical columns found.",
                font=("Arial", 16)
            )
            no_cat_label.pack(anchor="w", pady=5, padx=15)
        else:
            for col in categorical_cols:
                series = df[col]

                # Count unique values
                unique_values = series.dropna().unique()
                unique_count = len(unique_values)

                # Most common value
                value_counts = series.value_counts(dropna=True)
                if len(value_counts) > 0:
                    top_value = value_counts.index[0].strip()
                    top_freq = value_counts.iloc[0]
                else:
                    top_value = "N/A"
                    top_freq = 0

                # Column header
                col_label = ctk.CTkLabel(
                    unique_frame,
                    text=f"{col}: {unique_count} unique values",
                    font=("Arial", 15, "bold")
                )
                col_label.pack(anchor="w", pady=(10, 2), padx=15)

                total_non_null = len(series.dropna())
                if total_non_null > 0:
                    top_pct = (top_freq / total_non_null) * 100
                else:
                    top_pct = 0

                top_label = ctk.CTkLabel(
                    unique_frame,
                    text=f"• Most common: '{top_value}' ({top_freq} occurrences, {top_pct:.2f}%)",
                    font=("Arial", 14)
                )
                top_label.pack(anchor="w", pady=(0, 5), padx=20)

                # Scrollable list of values
                values_container = ctk.CTkScrollableFrame(unique_frame, height=120, fg_color="#333333")
                values_container.pack(fill="x", pady=(0, 10), padx=20)

                # Limit to avoid UI overload
                max_display = 200
                display_values = unique_values[:max_display]

                # Value counts for percentages
                value_counts_full = series.value_counts(dropna=True)

                for val in display_values:
                    freq = int(value_counts_full.get(val, 0))
                    pct = (freq / total_non_null * 100) if total_non_null > 0 else 0

                    item = ctk.CTkLabel(
                        values_container,
                        text=f"• {val}  —  {freq} ({pct:.2f}%)",
                        font=("Arial", 13)
                    )
                    item.pack(anchor="w")

                # If too many values, show a note
                if unique_count > max_display:
                    more_label = ctk.CTkLabel(
                        values_container,
                        text=f"... and {unique_count - max_display} more",
                        font=("Arial", 13, "italic")
                    )
                    more_label.pack(anchor="w")

        # --- NUMERIC STATS ---
        numeric_frame = ctk.CTkFrame(self.moreinfo_frame)
        numeric_frame.pack(fill="x", pady=10, padx=10)

        numeric_title = ctk.CTkLabel(
            numeric_frame,
            text="Numeric Statistics",
            font=("Arial", 20, "bold")
        )
        numeric_title.pack(anchor="w", pady=(0, 10), padx=10)

        df = self.app.manager.current_df
        types_dict = df_report["types"]

        numeric_cols = types_dict["numeric"]

        if len(numeric_cols) == 0:
            no_num_label = ctk.CTkLabel(
                numeric_frame,
                text="No numeric columns found.",
                font=("Arial", 16)
            )
            no_num_label.pack(anchor="w", pady=5, padx=15)
        else:
            for col in numeric_cols:
                series = df[col].dropna()

                if len(series) == 0:
                    empty_label = ctk.CTkLabel(
                        numeric_frame,
                        text=f"{col}: No numeric data available.",
                        font=("Arial", 15, "bold")
                    )
                    empty_label.pack(anchor="w", pady=(10, 2), padx=15)
                    continue

                # Compute stats
                min_val = series.min()
                max_val = series.max()
                mean_val = series.mean()
                std_val = series.std()
                median_val = series.median()
                q1 = series.quantile(0.25)
                q3 = series.quantile(0.75)

                # Column header
                col_label = ctk.CTkLabel(
                    numeric_frame,
                    text=f"{col}:",
                    font=("Arial", 15, "bold")
                )
                col_label.pack(anchor="w", pady=(10, 2), padx=15)

                # Stats table-like block
                stats_container = ctk.CTkFrame(numeric_frame, fg_color="#333333")
                stats_container.pack(fill="x", pady=(0, 10), padx=15)

                def add_stat(label, value):
                    stat_label = ctk.CTkLabel(
                        stats_container,
                        text=f"{label}: {value}",
                        font=("Arial", 13)
                    )
                    stat_label.pack(anchor="w", pady=2, padx=10)

                add_stat("Min", f"{min_val:.4f}")
                add_stat("Max", f"{max_val:.4f}")
                add_stat("Mean", f"{mean_val:.4f}")
                add_stat("Std", f"{std_val:.4f}")
                add_stat("Median", f"{median_val:.4f}")
                add_stat("Q1 (25%)", f"{q1:.4f}")
                add_stat("Q3 (75%)", f"{q3:.4f}")

    def update_charts(self, *args):
        """Generate charts for the selected column."""
        df = self.app.manager.current_df

        if df is None:
            return

        col = self.chart_column_var.get()

        if col == "" or col not in df.columns:
            self.chart_column_var.set(df.columns[0])
            col = self.chart_column_var.get()

        # --- CLEAN PREVIOUS CHARTS ---
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        self.chart_frame.update_idletasks()

        series = df[col].dropna()

        # --- NUMERIC OR CATEGORICAL ---
        is_numeric = pd.api.types.is_numeric_dtype(series)
        is_categorical = pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series)

        if not (is_numeric or is_categorical):
            msg = ctk.CTkLabel(
                self.chart_frame,
                text="Charts available only for numeric or categorical columns",
                font=("Arial", 16)
            )
            msg.pack(pady=20)
            return

        def clear_overlay(overlay):
            overlay.destroy()

        def render():
            if is_numeric:
                fig, axes = plt.subplots(1, 3, figsize=(12, 4))
                fig.patch.set_facecolor("#2b2b2b")

                # Histogram
                axes[0].hist(series, bins=30, color="#3a7bd5")
                axes[0].set_title("Histogram", color="white")
                axes[0].tick_params(colors="white")

                # Boxplot
                axes[1].boxplot(series, vert=True)
                axes[1].set_title("Boxplot", color="white")
                axes[1].tick_params(colors="white")

                # KDE
                try:
                    series.plot(kind="density", ax=axes[2], color="#d57b3a")
                    axes[2].set_title("Density (KDE)", color="white")
                    axes[2].tick_params(colors="white")
                except Exception:
                    axes[2].text(0.5, 0.5, "KDE unavailable", color="white")

            elif is_categorical:
                counts = series.value_counts()
                total = counts.sum()
                pct = counts / total * 100
                num_categories = len(counts)

                fig, axes = plt.subplots(1, 2, figsize=(12, 4))
                fig.patch.set_facecolor("#2b2b2b")

                # Bar chart (vertical)
                axes[0].bar(counts.index, counts.values, color="#3a7bd5")
                axes[0].set_title("Category Frequencies", color="white")
                axes[0].tick_params(axis="x", rotation=45, colors="white")
                axes[0].tick_params(axis="y", colors="white")

                # Add labels on absolute bar chart
                for rect, val in zip(axes[0].patches, counts.values):
                    height = rect.get_height()
                    bar_width = rect.get_width()

                    # Dynamic font size based on number of categories
                    if num_categories > 30:
                        break
                    elif num_categories > 20:
                        fontsize = 5
                    elif num_categories > 10:
                        fontsize = 7
                    else:
                        fontsize = 10

                    axes[0].text(
                        rect.get_x() + bar_width / 2,
                        height,
                        f"{val}",
                        ha="center",
                        va="bottom",
                        color="white",
                        fontsize=fontsize
                    )

                # Bar chart (horizontal)
                if len(counts) > 5:
                    axes[1].bar(pct.index, pct.values, color="#d57b3a")
                    axes[1].set_title("Category Share (%)", color="white")
                    axes[1].tick_params(axis="x", rotation=45, colors="white")
                    axes[1].tick_params(axis="y", colors="white")

                    # Add labels on percentage bar chart
                    for rect, val in zip(axes[1].patches, pct.values):
                        height = rect.get_height()
                        bar_width = rect.get_width()

                        # Dynamic font size based on number of categories
                        if num_categories > 30:
                            break
                        elif num_categories > 20:
                            fontsize = 5
                        elif num_categories > 10:
                            fontsize = 7
                        else:
                            fontsize = 10

                        axes[1].text(
                            rect.get_x() + bar_width / 2,
                            height,
                            f"{round(val,1)}%",
                            ha="center",
                            va="bottom",
                            color="white",
                            fontsize=fontsize
                        )

                # Pie chart only if few categories
                else:
                    axes[1].pie(counts.values, labels=counts.index, autopct="%1.1f%%")
                    axes[1].set_title("Category Share", color="white")

            for ax in axes:
                ax.set_facecolor("#1f1f1f")

            fig.tight_layout()

            # Embed directly in chart_frame
            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(fill="both", expand=True)

            overlay = ctk.CTkFrame(self.chart_frame, fg_color="transparent")
            overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

            canvas.draw()

            plt.close(fig)

            self.chart_frame.after(100, clear_overlay, overlay)

        # Render after Tk finishes clearing old widgets
        self.chart_frame.after(1, render)

    def update_correlation(self):
        if self.prev_corr_selection == self.corr_type_var.get():
            return
        else:
            self.prev_corr_selection = self.corr_type_var.get()

        df = self.app.manager.current_df

        if df is None:
            return

        # Clear previous content
        for widget in self.correlation_frame.winfo_children():
            widget.destroy()

        def show_corr_message(text):
            msg = ctk.CTkLabel(
                self.correlation_frame,
                text=text,
                font=("Arial", 20, "bold")
            )
            msg.pack(pady=40)

        corr_type = self.corr_type_var.get()

        if corr_type == "Full":
            cols = df.columns
            corr = pd.DataFrame(np.zeros((len(cols), len(cols))), index=cols, columns=cols)

            for c1 in cols:
                for c2 in cols:
                    s1 = df[c1]
                    s2 = df[c2]

                    if c1 == c2:
                        corr.loc[c1, c2] = 1
                        continue

                    is_num1 = pd.api.types.is_numeric_dtype(s1)
                    is_num2 = pd.api.types.is_numeric_dtype(s2)
                    is_cat1 = pd.api.types.is_string_dtype(s1) or pd.api.types.is_object_dtype(s1)
                    is_cat2 = pd.api.types.is_string_dtype(s2) or pd.api.types.is_object_dtype(s2)

                    if is_num1 and is_num2:
                        corr.loc[c1, c2] = s1.corr(s2)

                    elif is_cat1 and is_cat2:
                        corr.loc[c1, c2] = cramers_v(s1, s2)

                    elif is_cat1 and is_num2:
                        corr.loc[c1, c2] = correlation_ratio(s1, s2)

                    elif is_num1 and is_cat2:
                        corr.loc[c1, c2] = correlation_ratio(s2, s1)

                    else:
                        corr.loc[c1, c2] = np.nan

        elif corr_type == "Numeric":
            numeric_df = df.select_dtypes(include="number")

            if numeric_df.shape[1] == 0:
                show_corr_message("No numeric columns available.")
                return

            corr = numeric_df.corr()

        elif corr_type == "Categorical":
            cat_df = df.select_dtypes(include=["object", "string"])

            if cat_df.shape[1] == 0:
                show_corr_message("No categorical columns available.")
                return

            cols = cat_df.columns
            corr = pd.DataFrame(np.zeros((len(cols), len(cols))), index=cols, columns=cols)

            for c1 in cols:
                for c2 in cols:
                    corr.loc[c1, c2] = cramers_v(cat_df[c1], cat_df[c2])

        def clear_overlay(overlay):
            overlay.destroy()

        def render():
            fig, ax = plt.subplots(figsize=(10, 8))
            fig.patch.set_facecolor("#2b2b2b")

            # Mask upper triangle
            mask = np.triu(np.ones_like(corr, dtype=bool))

            cmap = plt.get_cmap("coolwarm")

            heatmap = ax.imshow(
                corr,
                cmap=cmap,
                interpolation="nearest"
            )

            # Draw mask rectangles
            for i in range(len(corr)):
                for j in range(len(corr)):
                    if mask[i, j]:
                        ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=True, color="#2b2b2b"))

            # Axis labels
            ax.set_xticks(np.arange(len(corr.columns)))
            ax.set_yticks(np.arange(len(corr.columns)))

            ax.set_xticklabels(corr.columns, rotation=45, ha="right", color="white")
            ax.set_yticklabels(corr.columns, color="white")

            ax.tick_params(axis="both", which="both", length=0)

            cbar = fig.colorbar(heatmap, ax=ax)
            cbar.ax.tick_params(colors="white")

            ax.set_anchor("C")

            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=self.correlation_frame)
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(fill="both", expand=True)

            overlay = ctk.CTkFrame(self.correlation_frame, fg_color="transparent")
            overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

            canvas.draw()

            fig.subplots_adjust(bottom=0.20)
            canvas.draw()

            self.correlation_frame.after(100, clear_overlay, overlay)

            plt.close(fig)

        self.correlation_frame.after(1, render)

    def update_missing_patterns(self, df_report):
        df = self.app.manager.current_df

        if df is None:
            return

        # Clear previous content
        for widget in self.missing_frame.winfo_children():
            widget.destroy()

        missing_df = df_report["missing"]
        missing_matrix = df.isna()
        missing_pct = missing_df["missing_pct"]
        missing_corr = missing_matrix.corr()

        if missing_df["missing_count"].sum() == 0:
            msg = ctk.CTkLabel(
                self.missing_frame,
                text="No missing data detected in the dataset.",
                font=("Arial", 20, "bold")
            )
            msg.pack(pady=40)
            self.missing_loaded = False
            return

        def clear_overlay(overlay):
            overlay.destroy()

        def render():
            fig, axes = plt.subplots(
                3,
                1,
                figsize=(12, 14),
                gridspec_kw={"height_ratios": [1, 1, 1.5]}
            )
            fig.patch.set_facecolor("#2b2b2b")

            # --- 1. Missing Matrix ---
            missing_cmap = ListedColormap([
                "#2b2b2b",
                "#ff6b6b"
            ])

            axes[0].imshow(missing_matrix, aspect="auto", cmap=missing_cmap)
            axes[0].set_title("Missing Matrix", color="white")
            axes[0].set_xticks([])
            axes[0].set_yticks([])
            axes[0].set_facecolor("#1f1f1f")

            # --- 2. Missing Bar Chart ---
            axes[1].bar(missing_pct.index, missing_pct.values, color="#d57b3a")
            axes[1].set_title("Missing Percentage", color="white")
            axes[1].tick_params(axis="x", rotation=45, colors="white")
            axes[1].tick_params(axis="y", colors="white")
            axes[1].set_facecolor("#1f1f1f")

            # Add labels
            for rect, val in zip(axes[1].patches, missing_pct.values):
                axes[1].text(
                    rect.get_x() + rect.get_width() / 2,
                    val,
                    f"{val:.1f}%",
                    ha="center",
                    va="bottom",
                    color="white",
                    fontsize=8
                )

            # --- 3. Missing Correlation Heatmap ---
            cmap = plt.get_cmap("coolwarm")

            heatmap = axes[2].imshow(
                missing_corr,
                cmap=cmap,
                interpolation="nearest",
                aspect="equal"
            )

            axes[2].set_title("Missing Correlation", color="white")
            axes[2].set_facecolor("#1f1f1f")

            axes[2].set_xticks(np.arange(len(missing_corr.columns)))
            axes[2].set_yticks(np.arange(len(missing_corr.columns)))

            axes[2].set_xticklabels(
                missing_corr.columns,
                rotation=45,
                ha="right",
                color="white"
            )
            axes[2].set_yticklabels(
                missing_corr.columns,
                color="white"
            )

            axes[2].tick_params(axis="both", which="both", length=0)

            # Center the heatmap inside its subplot
            axes[2].set_anchor("C")

            # Create a dedicated colorbar axis
            colorbar_ax = axes[2].inset_axes([1.02, 0.0, 0.035, 1.0])

            colorbar = fig.colorbar(heatmap, cax=colorbar_ax)
            colorbar.ax.tick_params(colors="white")

            # Adjust layout
            fig.tight_layout(
                rect=[0.03, 0.03, 0.97, 0.97]
            )

            # Embed in Tkinter
            canvas = FigureCanvasTkAgg(fig, master=self.missing_frame)
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(fill="both", expand=True)

            overlay = ctk.CTkFrame(self.missing_frame, fg_color="transparent")
            overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

            canvas.draw()

            plt.close(fig)

            self.missing_frame.after(100, clear_overlay, overlay)

        self.missing_frame.after(1, render)


