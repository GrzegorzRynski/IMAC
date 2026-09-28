import os
import textwrap
from pathlib import Path

import CTkMessagebox
import customtkinter as ctk
from tkinter import filedialog
from CTkListbox import CTkListbox
import pandas as pd

from load_data import load_data_file


class LoadDataView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)

        self.app = app

        self.up_to_date = False

        # --- TITLE ---
        title = ctk.CTkLabel(self, text="Load Dataset", font=("Arial", 22, "bold"))
        title.pack(pady=20)

        # --- BUTTON TO LOAD FILE ---
        load_btn = ctk.CTkButton(self, text="Select Data File", command=self.load_file_dialog)
        load_btn.pack(pady=10)

        # --- CURRENT DATASET INFO ---
        self.current_info_label = ctk.CTkLabel(self, text="Current Dataset:", font=("Arial", 22, "bold"))
        self.current_info_label.pack(pady=20)

        current_info_frame = ctk.CTkFrame(self, fg_color="transparent")
        current_info_frame.pack(pady=10)

        self.current_info_name_label = ctk.CTkLabel(current_info_frame, text="Dataset Name:", font=("Arial", 22, "bold"))
        self.current_info_name_label.grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)

        self.current_info_name_display = ctk.CTkLabel(current_info_frame, text="", font=("Arial", 22), wraplength=400)
        self.current_info_name_display.grid(row=0, column=1, sticky="w", pady=5)

        self.current_info_row_label = ctk.CTkLabel(current_info_frame, text="Rows:", font=("Arial", 22, "bold"))
        self.current_info_row_label.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)

        self.current_info_row_display = ctk.CTkLabel(current_info_frame, text="", font=("Arial", 22))
        self.current_info_row_display.grid(row=1, column=1, sticky="w", pady=5)

        self.current_info_column_label = ctk.CTkLabel(current_info_frame, text="Columns:", font=("Arial", 22, "bold"))
        self.current_info_column_label.grid(row=2, column=0, sticky="w", padx=(0, 10), pady=5)

        self.current_info_column_display = ctk.CTkLabel(current_info_frame, text="", font=("Arial", 22))
        self.current_info_column_display.grid(row=2, column=1, sticky="w", pady=5)

        # --- RECENT FILES LIST ---
        self.recent_label = ctk.CTkLabel(self, text="Known Datasets:", font=("Arial", 22, "bold"))
        self.recent_label.pack(pady=10)

        self.known_list = CTkListbox(self, width=600, height=200)

        self.known_list.pack(pady=10, fill="x", padx=100)

        # --- BUTTON: LOAD FROM RECENT ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)

        load_recent_btn = ctk.CTkButton(btn_frame, text="Load Selected Known Dataset", command=self.load_known)
        load_recent_btn.pack(side="left", padx=(10,5))

        refresh_btn = ctk.CTkButton(btn_frame, text="Refresh", command=self.refresh_known)
        refresh_btn.pack(side="left", padx=(5,10))

        self.app.manager.register_update_callback(self.on_update)

        self.update_known_list()
        self.show_current_info()

    def load_file_dialog(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Data Files", ["*.csv", "*.data"]), ("All Files", "*.*")]
        )

        if not file_path:
            return

        file_path = str(Path(file_path))

        try:
            df = load_data_file(file_path)
        except FileNotFoundError:

            CTkMessagebox.CTkMessagebox(
                title="Error",
                message="Could not load dataset.\nFile does not exist.",
                icon="cancel"
            )

            self.show_current_info()
            return

        except ValueError:

            CTkMessagebox.CTkMessagebox(
                title="Error",
                message="Could not load dataset.\nFile is not in a correct format or is unreadable.",
                icon="cancel"
            )

            self.show_current_info()
            return


        self.app.manager.load_df(df, file_path)

        self.show_current_info()
        self.update_known_list()

    def load_known(self):

        selected = self.known_list.get()

        if not selected or selected == "No known files yet.":
            return

        try:
            path = selected.split(" – ", 1)[1]
        except IndexError:
            return

        try:
            df = load_data_file(path)
        except FileNotFoundError:

            CTkMessagebox.CTkMessagebox(
                title="Error",
                message="Could not load known dataset.\nFile does not exist.",
                icon="cancel"
            )

            if str(Path(path)) in self.app.manager.remembered_locations:
                self.app.manager.remembered_locations.remove(str(Path(path)))
            self.app.manager.save_app_data()
            self.show_current_info()
            self.update_known_list()
            return

        except ValueError:

            CTkMessagebox.CTkMessagebox(
                title="Error",
                message="Could not load known dataset.\nFile is not in a correct format or is unreadable.",
                icon="cancel"
            )

            if str(Path(path)) in self.app.manager.remembered_locations:
                self.app.manager.remembered_locations.remove(str(Path(path)))
            self.app.manager.save_app_data()
            self.show_current_info()
            self.update_known_list()
            return

        self.app.manager.load_df(df, path)
        self.show_current_info()

    def refresh_known(self):

        self.app.manager.load_remembered_locations()

        self.update_known_list()

    def show_current_info(self):

        df = self.app.manager.original_df

        if df is not None:
            self.current_info_name_label.grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5, columnspan=1)
            self.current_info_name_label.configure(text="Dataset Name: ")

            self.current_info_name_display.grid(row=0, column=1, sticky="w", pady=5)
            self.current_info_name_display.configure(text=f"{self.app.manager.current_name}")

            self.current_info_row_label.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)
            self.current_info_row_label.configure(text="Rows: ")

            self.current_info_row_display.grid(row=1, column=1, sticky="w", pady=5)
            self.current_info_row_display.configure(text=f"{len(df)}")

            self.current_info_column_label.grid(row=2, column=0, sticky="w", padx=(0, 10), pady=5)
            self.current_info_column_label.configure(text="Columns: ")

            self.current_info_column_display.grid(row=2, column=1, sticky="w", pady=5)
            self.current_info_column_display.configure(text=f"{len(df.columns)}")

        else:
            self.current_info_name_display.grid_remove()
            self.current_info_row_label.grid_remove()
            self.current_info_row_display.grid_remove()
            self.current_info_column_label.grid_remove()
            self.current_info_column_display.grid_remove()

            self.current_info_name_label.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=5)
            self.current_info_name_label.configure(text="No Dataset Selected")

    def update_known_list(self):

        self.known_list.delete(0, "end")

        if not self.app.manager.remembered_locations:
            self.known_list.insert("end", "No recent files yet.")
            return

        for path in self.app.manager.remembered_locations:
            filename = os.path.basename(path)
            display_text = f"{filename} – {path}"
            self.known_list.insert("end", display_text)

    def update_view(self):
        if self.app.current_view == self and not self.up_to_date:
            self.show_current_info()
            self.up_to_date = True

    def on_update(self):
        self.up_to_date = False
        self.update_view()
