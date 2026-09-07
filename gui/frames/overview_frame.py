import customtkinter as ctk
from tkinter import ttk

import pandas as pd
from pandas.core.computation import align

from init_analitics.init_analytics import report


class OverviewView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.page_size = 1000
        self.current_page = 0
        self.filtered_df = None

        # --- TITLE ---
        title = ctk.CTkLabel(self, text="Dataset Overview", font=("Arial", 24, "bold"))
        title.pack(pady=(10, 20))

        # --- NAME DISPLAY ---
        self.name_label = ctk.CTkLabel(self, text="No Dataset Selected", font=("Arial", 16), wraplength=1200)
        self.name_label.pack(pady=10)

        # --- INFO BAR ---
        self.info_label = ctk.CTkLabel(self, text="", font=("Arial", 16))
        self.info_label.pack(pady=10)

        self.tabs = ctk.CTkTabview(self, fg_color="transparent")
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)

        tables_tab = self.tabs.add("Tables")
        tables_tab.configure(fg_color="transparent")

        moreinfo_tab = self.tabs.add("More Info")

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
        table_container = ctk.CTkFrame(split_frame)
        table_container.grid(row=0, column=0, sticky="nswe", padx=10)

        # Scrollbars
        self.table_scroll_y = ctk.CTkScrollbar(table_container, orientation="vertical")
        self.table_scroll_y.pack(side="right", fill="y")

        self.table_scroll_x = ctk.CTkScrollbar(table_container, orientation="horizontal")
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
            table_container,
            show="headings",
            yscrollcommand=self.table_scroll_y.set,
            xscrollcommand=self.table_scroll_x.set
        )
        self.table.pack(fill="both", expand=True)

        self.table.tag_configure("missing_row", background="#662222")

        self.table_scroll_y.configure(command=self.table.yview)
        self.table_scroll_x.configure(command=self.table.xview)

        pagination_frame = ctk.CTkFrame(table_container, fg_color="transparent")
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
        self.stats_table.pack(fill="both", expand=True)

        self.stats_scroll_y.configure(command=self.stats_table.yview)

        # Define columns

        self.stats_table["columns"] = ("Column", "Type", "Missing", "Missing %", "Unusual")

        self.stats_table.heading("Column", text="Column")
        self.stats_table.heading("Type", text="Type")
        self.stats_table.heading("Missing", text="Missing")
        self.stats_table.heading("Missing %", text="Missing %")
        self.stats_table.heading("Unusual", text="Unusual Tokens")

        self.stats_table.column("Column", width=100, anchor="w")
        self.stats_table.column("Type", width=60, anchor="w")
        self.stats_table.column("Missing", width=60, anchor="center")
        self.stats_table.column("Missing %", width=80, anchor="center")
        self.stats_table.column("Unusual", width=80, anchor="center")

        reset_btn = ctk.CTkButton(
            tables_tab,
            text="Reset Tables",
            command=self.reset_tables,
            fg_color="#3a7bd5",
            hover_color="#2f5fa8"
        )
        reset_btn.pack(pady=10)

        # Register auto-update
        self.app.manager.register_update_callback(self.update_view)

        # ---------------------- MORE INFO ---------------------------------------------------------

        self.moreinfo_frame = ctk.CTkScrollableFrame(moreinfo_tab, fg_color="transparent")
        self.moreinfo_frame.pack(fill="both", expand=True, padx=50, pady=50)

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
            values = [index+1] + list(row.values)

            has_missing = any(
                v is None or
                (isinstance(v, float) and pd.isna(v)) or
                (isinstance(v, str) and v.strip() == "")
                for v in row.values
            )

            if has_missing:
                self.table.insert("", "end", values=values, tags=("missing_row",))
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
        df_report = report(df)
        missing_df = df_report["missing"]
        types_dict = df_report["types"]

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

    def update_view(self):
        df = self.app.manager.current_df

        # Clear tables
        for row in self.table.get_children():
            self.table.delete(row)

        for row in self.stats_table.get_children():
            self.stats_table.delete(row)

        if df is None:
            self.info_label.pack_forget()
            self.name_label.configure(text="No Dataset Loaded")
            self.table["columns"] = []
            self.stats_table["columns"] = []
            return

        # --- NAME ---
        self.name_label.configure(text=f"Dataset: {self.app.manager.current_name}")

        # --- REPORT ---
        df_report = report(df)
        missing_df = df_report["missing"]
        types_dict = df_report["types"]

        # --- INFO BAR ---
        missing_percent = df.isna().sum().sum() / df.size * 100
        self.info_label.pack(pady=10)
        self.info_label.configure(
            text=f"Rows: {len(df)} | Columns: {len(df.columns)} | "
                 f"Missing: {missing_percent:.2f}%"
        )

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
                self.table.insert("", "end", values=[index+1] + list(row.values), tags=("missing_row",))
            else:
                self.table.insert("", "end", values=[index+1] + list(row.values))

        for col in df.columns:
            self.table.heading(col, text=col, command=lambda c=col: self.sort_treeview(self.table, c, False))

        # --- STATS TABLE ---
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

        for col in ("Column", "Type", "Missing", "Missing %", "Unusual"):
            self.stats_table.heading(col, text=col, command=lambda c=col: self.sort_treeview(self.stats_table, c, False))

        self.current_page = 0
        self.filtered_df = None
        self.load_page()

        self.update_more_info(df_report)

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

        # --- UNIQUE VALUES ---
        unique_frame = ctk.CTkFrame(self.moreinfo_frame)
        unique_frame.pack(fill="x", pady=10, padx=10)

        unique_title = ctk.CTkLabel(
            unique_frame,
            text="Unique Categorical Values",
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


