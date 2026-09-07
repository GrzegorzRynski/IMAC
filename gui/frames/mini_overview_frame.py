import customtkinter as ctk

class MiniOverviewView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # --- TITLE ---
        self.title = ctk.CTkLabel(self, text="Dataset Overview", font=("Arial", 20, "bold"))
        self.title.pack(pady=(10, 20), padx=50)

        # --- EMPTY STATE ---
        self.empty_label = ctk.CTkLabel(self, text="No Dataset Selected", font=("Arial", 16))
        self.empty_label.pack(pady=10)

        # --- FULL STATE ELEMENTS ---
        self.name_label = ctk.CTkLabel(self, text="", font=("Arial", 16), wraplength=220)
        self.shape_label = ctk.CTkLabel(self, text="", font=("Arial", 16))
        self.missing_label = ctk.CTkLabel(self, text="", font=("Arial", 16))
        self.types_label = ctk.CTkLabel(self, text="", font=("Arial", 16))

        # Register auto-update
        self.app.manager.register_update_callback(self.update_view)

        # Initial update
        self.update_view()

    def hide_full_state(self):
        self.name_label.pack_forget()
        self.shape_label.pack_forget()
        self.missing_label.pack_forget()
        self.types_label.pack_forget()

    def show_full_state(self):
        self.name_label.pack(pady=5)
        self.shape_label.pack(pady=5)
        self.missing_label.pack(pady=5)
        self.types_label.pack(pady=10)

    def update_view(self):
        df = self.app.manager.current_df

        if df is None:
            # EMPTY STATE
            self.empty_label.pack(pady=10)
            self.hide_full_state()
            return

        # FULL STATE
        self.empty_label.pack_forget()
        self.show_full_state()

        # Name
        self.name_label.configure(text=f"Dataset: {self.app.manager.current_name}")

        # Shape
        self.shape_label.configure(text=f"Rows: {len(df)}   Columns: {len(df.columns)}")

        # Missingness
        missing_percent = df.isna().sum().sum() / df.size * 100
        self.missing_label.configure(text=f"Missing: {missing_percent:.2f}%")

        # Types summary
        types = ", ".join(df.dtypes.astype(str).unique())
        self.types_label.configure(text=f"Types: {types}")