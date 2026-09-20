import history_manager
from history_manager import HistoryManager
import customtkinter as ctk

class HistoryView(ctk.CTkFrame):

    ROW_HEIGHT = 170
    MAX_VISIBLE_BRANCHES = 3
    BRANCH_SPACING = 5

    def __init__(self, parent, history: history_manager.HistoryManager):
        super().__init__(parent)

        self.history = history
        self.pack_propagate(False)

        title = ctk.CTkLabel(
            self,
            text="History",
            font=("Arial", 18, "bold")
        )
        title.pack(anchor="n", padx=10, pady=(5, 10))

        self.main_frame = ctk.CTkScrollableFrame(self)
        self.main_frame.pack(fill="both", expand=True)

        self.left_column = ctk.CTkFrame(
            self.main_frame,
            width=150
        )
        self.left_column.pack(side="left", fill="y")

        self.right_column = ctk.CTkFrame(
            self.main_frame
        )
        self.right_column.pack(
            side="left",
            fill="both",
            expand=True
        )

    def rename_branch(self, branch_rename_field, branch_rename_cancel_button,
                      branch_rename_confirm_button,branch_id, branch_name):
        self.hide_rename(branch_rename_field, branch_rename_cancel_button, branch_rename_confirm_button)
        if self.history.branch_names[branch_id] == branch_name:
            return
        self.history.rename_branch(branch_id, branch_name)
        self.render_history()

    def hide_rename(self, branch_rename_field, branch_rename_cancel_button,
                    branch_rename_confirm_button):
        branch_rename_field.grid_remove()
        branch_rename_cancel_button.grid_remove()
        branch_rename_confirm_button.grid_remove()

    def reveal_rename(self, branch_rename_field, branch_rename_cancel_button,
                      branch_rename_confirm_button, branch_delete_label, branch_id, branch_name):
        self.hide_delete(branch_delete_label, branch_rename_cancel_button, branch_rename_confirm_button)
        branch_rename_cancel_button.configure(
            command=lambda
                field=branch_rename_field,
                can_button=branch_rename_cancel_button,
                con_button=branch_rename_confirm_button:
            self.hide_rename(
                field,
                can_button,
                con_button
            )
        )

        branch_rename_confirm_button.configure(
            command=lambda
                field=branch_rename_field,
                can_button=branch_rename_cancel_button,
                con_button=branch_rename_confirm_button,
                br_id=branch_id,
                field_ref=branch_rename_field:
            self.rename_branch(
                field,
                can_button,
                con_button,
                br_id,
                field_ref.get()
            )
        )

        branch_rename_field.grid(row=2, column=0, columnspan=4, padx=5, pady=5)
        branch_rename_cancel_button.grid(row=3, column=1, padx=5, pady=5)
        branch_rename_confirm_button.grid(row=3, column=2, padx=5, pady=5)
        branch_rename_field.delete(0, "end")
        branch_rename_field.insert(0, branch_name)

    def delete_branch(self, branch_rename_field, branch_rename_cancel_button,
                      branch_rename_confirm_button,branch_id):
        self.hide_delete(branch_rename_field, branch_rename_cancel_button, branch_rename_confirm_button)
        self.history.delete_branch(branch_id)
        self.render_history()

    def hide_delete(self, branch_delete_field, branch_delete_cancel_button,
                    branch_delete_confirm_button):
        branch_delete_field.grid_remove()
        branch_delete_cancel_button.grid_remove()
        branch_delete_confirm_button.grid_remove()

    def reveal_delete(self, branch_delete_prompt, branch_delete_cancel_button,
                      branch_delete_confirm_button, branch_rename_field, branch_id):
        self.hide_rename(branch_rename_field, branch_delete_cancel_button, branch_delete_confirm_button)
        branch_delete_cancel_button.configure(
            command=lambda
                field=branch_delete_prompt,
                can_button=branch_delete_cancel_button,
                con_button=branch_delete_confirm_button:
            self.hide_delete(
                field,
                can_button,
                con_button
            )
        )

        branch_delete_confirm_button.configure(
            command=lambda
                field=branch_delete_prompt,
                can_button=branch_delete_cancel_button,
                con_button=branch_delete_confirm_button,
                br_id=branch_id:
            self.delete_branch(
                field,
                can_button,
                con_button,
                br_id,
            )
        )

        branch_delete_prompt.grid(row=2, column=0, columnspan=4, padx=5, pady=5)
        branch_delete_cancel_button.grid(row=3, column=1, padx=5, pady=5)
        branch_delete_confirm_button.grid(row=3, column=2, padx=5, pady=5)

    def move_branch(self, branch_id, new_branch_id):
        if new_branch_id < 0 or new_branch_id >= len(self.history.branches):
            return
        self.history.swap_branches(branch_id, new_branch_id)
        self.render_history()

    def copy_branch(self, branch_id):
        self.history.create_branch_from(branch_id)
        self.render_history()

    def render_history(self):

        branches = self.history.branches
        branch_names = self.history.branch_names

        visible = min(
            len(branches),
            self.MAX_VISIBLE_BRANCHES
        )

        height = visible * (self.ROW_HEIGHT + 4 * self.BRANCH_SPACING) + 69

        self.configure(height=height)

        for widget in self.left_column.winfo_children():
            widget.destroy()

        for widget in self.right_column.winfo_children():
            widget.destroy()

        def format_args(args):
            if not args:
                return ""

            return "\n".join(
                f"{k}: {v}"
                for k, v in args.items()
            )

        for branch_id, branch in enumerate(branches):

            try:
                branch_name = branch_names[branch_id]
            except IndexError:
                branch_name = "Branch " + str(branch_id)

            branch_label_frame = ctk.CTkFrame(
                self.left_column,
                height = self.ROW_HEIGHT + self.BRANCH_SPACING*4,
                width = 150,
                fg_color="#131313",
            )

            branch_label_frame.pack(side="top", fill="x", padx=5, pady=self.BRANCH_SPACING)

            branch_label_frame.grid_rowconfigure(0, weight=0, pad=5)
            branch_label_frame.grid_rowconfigure(1, weight=1)
            branch_label_frame.grid_rowconfigure(2, weight=0)
            branch_label_frame.grid_rowconfigure(3, weight=0)
            branch_label_frame.grid_rowconfigure(4, weight=0)
            branch_label_frame.grid_rowconfigure(5, weight=1)

            branch_label_frame.grid_columnconfigure(0, weight=1)
            branch_label_frame.grid_columnconfigure(1, weight=1)
            branch_label_frame.grid_columnconfigure(2, weight=1)
            branch_label_frame.grid_columnconfigure(3, weight=1)

            branch_label_frame.grid_propagate(False)

            branch_label = ctk.CTkLabel(
                branch_label_frame,
                height = self.ROW_HEIGHT + self.BRANCH_SPACING*4,
                text=branch_name,
                wraplength=150,
                font=("Arial", 16, "bold"),
                padx=5
            )

            branch_label.grid(row=1, column=0, columnspan=4)

            branch_rename_field = ctk.CTkEntry(
                branch_label_frame,
                height=30
            )

            cancel_button = ctk.CTkButton(
                branch_label_frame,
                height=20,
                width=30,
                text="X",
                fg_color="red"
            )

            confirm_button = ctk.CTkButton(
                branch_label_frame,
                height=20,
                width=30,
                text="✔",
                fg_color="green"
            )

            delete_branch_label = ctk.CTkLabel(
                branch_label_frame,
                font=("Arial", 12, "bold"),
                text="Confirm delete?",
                text_color="red"
            )

            branch_rename_button = ctk.CTkButton(
                branch_label_frame,
                width=50,
                height=20,
                text="rename",
                font=("Arial", 10),
                command=lambda
                    field=branch_rename_field,
                    can_button=cancel_button,
                    con_button=confirm_button,
                    del_field=delete_branch_label,
                    br_id = branch_id,
                    name=branch_name:
                    self.reveal_rename(field, can_button, con_button, del_field, br_id, name)
            )

            branch_rename_button.grid(row=4, column=1, pady=5)

            branch_copy_button = ctk.CTkButton(
                branch_label_frame,
                width=50,
                height=20,
                text="copy",
                font=("Arial", 10),
                command=lambda
                    br_id=branch_id:
                    self.copy_branch(
                        br_id
                    )
            )

            branch_copy_button.grid(row=4, column=2, pady=5)

            branch_moveup_button = ctk.CTkButton(
                branch_label_frame,
                width=20,
                height=20,
                text="↑",
                command=lambda
                    br_id=branch_id:
                    self.move_branch(
                        br_id,
                        br_id - 1
                    )
            )

            branch_moveup_button.grid(row=4, column=0, pady=5)

            branch_movedown_button = ctk.CTkButton(
                branch_label_frame,
                width=20,
                height=20,
                text="↓",
                command=lambda
                    br_id=branch_id:
                self.move_branch(
                    br_id,
                    br_id + 1
                )
            )

            branch_movedown_button.grid(row=4, column=3, pady=5)

            delete_branch_button = ctk.CTkButton(
                branch_label_frame,
                height=20,
                width=20,
                text="X",
                fg_color="red",
                command = lambda
                    field=branch_rename_field,
                    label=delete_branch_label,
                    can_button=cancel_button,
                    con_button=confirm_button,
                    br_id=branch_id:
                self.reveal_delete(label, can_button, con_button, field, br_id)
            )

            delete_branch_button.grid(row=0, column=3)

            row_frame = ctk.CTkScrollableFrame(
                self.right_column,
                orientation="horizontal",
                height=self.ROW_HEIGHT
            )
            row_frame.pack(side="top", fill="x", padx=5, pady=self.BRANCH_SPACING)

            for entry in branch:
                card = ctk.CTkButton(
                    row_frame,
                    width=240,
                    height=self.ROW_HEIGHT,
                    text=(
                        f"{entry['name']}\n\n"
                        f"{entry['desc']}\n\n"
                        f"{format_args(entry['args'])}"
                    )
                )

                card.pack(
                    side="left",
                    padx=5
                )