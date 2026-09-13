import os
import tkinter
from json import JSONDecodeError
from pathlib import Path

import CTkMessagebox
import pandas as pd
import json

from load_data import load_data_file


class ImputationManager:
    def __init__(self):

        self.remembered_locations = []
        self.current_df = None
        self.original_df = None
        self.current_name = ""
        self.current_path = ""
        self.df_history = []
        self.current_index = 0

        self.on_load_callbacks = []
        self.on_change_callbacks = []

        self.data_file = "app_data.json"
        self.data_folder = "data"
        self.data = None

    def register_load_callback(self, callback):
        if callback not in self.on_load_callbacks:
            self.on_load_callbacks.append(callback)

    def notify_load(self):
        for cb in self.on_load_callbacks:
            cb()

    def register_update_callback(self, callback):
        if callback not in self.on_change_callbacks:
            self.on_change_callbacks.append(callback)

    def notify_change(self):
        for cb in self.on_change_callbacks:
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

        current_path = self.data.get("last_used_file", None)

        if current_path is not None and current_path != "":
            try:
                df = load_data_file(current_path)
            except FileNotFoundError:

                CTkMessagebox.CTkMessagebox(
                    title="Error",
                    message="Could not load last used dataset.\nFile was moved or deleted.",
                    icon="cancel"
                )

                self.save_app_data()

                return

            except ValueError:

                CTkMessagebox.CTkMessagebox(
                    title="Error",
                    message="Could not load last used dataset.\nFile is not in a correct format or is unreadable.",
                    icon="cancel"
                )

                self.save_app_data()

                return

            self.load_df(df, current_path)

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

        data = {
            "recent_files": self.remembered_locations,
            "last_used_file": self.current_path
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


    def load_df(self, df, df_path):

        self.current_name = Path(df_path).name
        self.current_path = df_path
        self.current_df = df
        self.original_df = df
        self.df_history.clear()
        self.df_history.append(df)
        self.current_index = len(self.df_history)-1

        if str(df_path) not in self.remembered_locations:
            self.remembered_locations.append(str(df_path))

        self.save_app_data()
        self.notify_load()
        self.notify_change()