from sys import maxsize

import CTkMessagebox
import customtkinter as ctk

import imputation_manager
from gui.components.history_view import HistoryView
from gui.frames.load_data_frame import LoadDataView
from gui.frames.mini_overview_frame import MiniOverviewView
from gui.frames.overview_frame import OverviewView


class ImputationApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.manager = imputation_manager.ImputationManager()
        self.after(10, self.manager.load_app_data)

        self.views = {}
        self.view_change = {}

        self.mini_overview = None
        self.current_view = None
        self.current_view_name = None

        # --- WINDOW CONFIG ---
        self.title("Imputation Methods Analysis Center")
        self.geometry("1600x900")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # --- GRID CONFIG ---
        self.grid_columnconfigure(0, weight=0)  # sidebar
        self.grid_columnconfigure(1, weight=1)  # main content
        self.grid_columnconfigure(2, weight=0)  # mini overview
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nswe")

        self.sidebar_title = ctk.CTkLabel(
            self.sidebar,
            text="IMPUTATION CENTER",
            font=("Arial", 20, "bold")
        )
        self.sidebar_title.pack(pady=20, padx=10)

        # Placeholder buttons (later: load data, missingness, imputations, evaluation)
        self.btn_overview = ctk.CTkButton(self.sidebar, text="Data Overview", font=("Arial", 15, "bold"),
                                      command=self.show_overview_view)
        self.btn_overview.pack(pady=10, fill="x", padx=10)

        self.btn_load = ctk.CTkButton(self.sidebar, text="Load Data", font=("Arial", 15, "bold"), command=self.show_load_data_view)
        self.btn_load.pack(pady=10, fill="x", padx=10)

        self.btn_missing = ctk.CTkButton(self.sidebar, text="Missingness", font=("Arial", 15, "bold"))
        self.btn_missing.pack(pady=10, fill="x", padx=10)

        self.btn_impute = ctk.CTkButton(self.sidebar, text="Imputation", font=("Arial", 15, "bold"))
        self.btn_impute.pack(pady=10, fill="x", padx=10)

        self.btn_evaluate = ctk.CTkButton(self.sidebar, text="Evaluation", font=("Arial", 15, "bold"))
        self.btn_evaluate.pack(pady=10, fill="x", padx=10)

        # --- MAIN CONTENT AREA ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=1, sticky="nswe", padx=20, pady=20)

        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # --- MINI OVERVIEW AREA ---
        self.mini_overview_frame = ctk.CTkFrame(self)
        self.mini_overview_frame.grid(row=0, column=2, sticky="nswe")

        self.show_overview_view()

    def switch_view(self, name):
        if self.current_view is not None and self.current_view == self.views[name]:
            return

        if self.current_view:
            self.current_view.grid_remove()

        self.current_view = self.views[name]
        self.current_view.grid(row=0, column=0, sticky="nswe")
        self.current_view.update_view()

    def register_view_change(self, name, callback):
        self.view_change.append(callback)

    def show_overview_view(self):
        if "overview" not in self.views.keys():
            self.views["overview"] = OverviewView(self.main_frame, self)

        self.switch_view("overview")
        self.mini_overview_frame.grid_remove()

    def show_mini_overview_view(self):
        if self.mini_overview is None:
            self.mini_overview = MiniOverviewView(self.mini_overview_frame, self)
            self.mini_overview.pack(fill="both", expand=True)

        self.mini_overview_frame.grid()

    def show_load_data_view(self):
        if "load" not in self.views.keys():
            self.views["load"] = LoadDataView(self.main_frame, self)

        self.switch_view("load")
        self.show_mini_overview_view()

if __name__ == "__main__":
    app = ImputationApp()
    app.mainloop()