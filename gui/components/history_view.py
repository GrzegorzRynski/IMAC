import history_manager
from history_manager import HistoryManager
import customtkinter as ctk

class HistoryView(ctk.CTkFrame):

    ROW_HEIGHT = 200
    BRANCH_SPACING = 5
    MAX_VISIBLE_BRANCHES = 3
    LEFT_COLUMN_WIDTH = 150
    TITLE_HEIGHT = 40
    ADD_BUTTON_HEIGHT = 70

    BRANCH_PITCH = ROW_HEIGHT + 2 * BRANCH_SPACING

    # Branch colors
    ACTIVE_BRANCH_COLOR = "#1F6AA5"
    INACTIVE_BRANCH_COLOR = "#263542"

    # Action colors
    COMPLETED_ACTION_COLOR = "#245D87"
    CURRENT_ACTION_COLOR = "#2F8FD8"
    FUTURE_ACTION_COLOR = "#30363B"

    # Hover colors
    COMPLETED_ACTION_HOVER = "#2D719F"
    CURRENT_ACTION_HOVER = "#3B9BE5"
    FUTURE_ACTION_HOVER = "#3A4147"

    INACTIVE_ACTION_HOVER = "#304252"

    # Current action border
    CURRENT_ACTION_BORDER_COLOR = "#70C1FF"
    CURRENT_ACTION_BORDER_WIDTH = 3

    DEFAULT_ACTION_BORDER_WIDTH = 0

    # Branch control buttons
    BRANCH_BUTTON_COLOR = "#3A4A56"
    BRANCH_BUTTON_HOVER = "#4A5D6A"

    BRANCH_MOVE_COLOR = "#344550"
    BRANCH_MOVE_HOVER = "#465B68"

    BRANCH_DELETE_COLOR = "#B83A3A"
    BRANCH_DELETE_HOVER = "#D14A4A"

    BRANCH_CONFIRM_COLOR = "#2E8B57"
    BRANCH_CONFIRM_HOVER = "#3AAE6F"

    BRANCH_CANCEL_COLOR = "#8F3434"
    BRANCH_CANCEL_HOVER = "#B64242"

    def __init__(self, parent, history: history_manager.HistoryManager, scroll = None):
        super().__init__(parent)

        self.configure(fg_color="transparent")

        self.scroll_parent = scroll

        self.history = history
        self.pack_propagate(False)

        self.title_frame = ctk.CTkFrame(
            self,
            height=self.TITLE_HEIGHT,
            fg_color="transparent"
        )

        self.title_frame.pack(
            fill="x"
        )

        self.title_frame.pack_propagate(False)

        title = ctk.CTkLabel(
            self.title_frame,
            text="History",
            font=("Arial", 18, "bold")
        )

        title.pack(
            expand=True
        )

        self.main_frame = ctk.CTkScrollableFrame(
            self,
            height=self.MAX_VISIBLE_BRANCHES * self.BRANCH_PITCH
        )

        self.main_frame.pack(
            fill="both",
            expand=True
        )

        self.history.register_view_update_callback(self.render_history)

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

        self.scroll_parent._parent_canvas.yview_moveto(1.0)

    def select_action(self, branch_id, action_id):
        if self.history.select_action(branch_id, action_id):
            self.render_history()
        
    def create_branch(self):
        self.history.create_new_branch()
        self.render_history()

        self.main_frame._parent_canvas.yview_moveto(1.0)
        self.scroll_parent._parent_canvas.yview_moveto(1.0)

    def render_history(self):

        branches = self.history.branches
        branch_names = self.history.branch_names

        visible = min(
            len(branches),
            self.MAX_VISIBLE_BRANCHES
        )

        content_height = visible * self.BRANCH_PITCH + self.ADD_BUTTON_HEIGHT
        height = self.TITLE_HEIGHT + content_height

        self.configure(height=height)
        self.main_frame.configure(height=content_height)

        for widget in self.main_frame.winfo_children():
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

            branch_row = ctk.CTkFrame(
                self.main_frame,
                height=self.ROW_HEIGHT,
            )

            branch_row.pack(
                fill="x",
                padx=5,
                pady=self.BRANCH_SPACING
            )

            branch_row.pack_propagate(False)

            is_active_branch = branch_id == self.history.current_branch

            branch_color = (
                self.ACTIVE_BRANCH_COLOR
                if is_active_branch
                else self.INACTIVE_BRANCH_COLOR
            )

            branch_label_frame = ctk.CTkFrame(
                branch_row,
                width=self.LEFT_COLUMN_WIDTH,
                height=self.ROW_HEIGHT,
                fg_color=branch_color
            )

            branch_label_frame.pack(
                side="left",
                fill="y"
            )

            branch_label_frame.pack_propagate(False)

            branch_label_frame.grid_rowconfigure(0, weight=0, pad=5)
            branch_label_frame.grid_rowconfigure(1, weight=1)
            branch_label_frame.grid_rowconfigure(2, weight=0)
            branch_label_frame.grid_rowconfigure(3, weight=0)
            branch_label_frame.grid_rowconfigure(4, weight=0)

            branch_label_frame.grid_columnconfigure(0, weight=1)
            branch_label_frame.grid_columnconfigure(1, weight=1)
            branch_label_frame.grid_columnconfigure(2, weight=1)
            branch_label_frame.grid_columnconfigure(3, weight=1)

            branch_label = ctk.CTkLabel(
                branch_label_frame,
                text=branch_name,
                wraplength=self.LEFT_COLUMN_WIDTH - 10,
                font=("Arial", 16, "bold"),
                padx=5
            )

            branch_label.grid(
                row=1,
                column=0,
                columnspan=4,
                sticky="nsew"
            )

            branch_rename_field = ctk.CTkEntry(
                branch_label_frame,
                height=30
            )

            cancel_button = ctk.CTkButton(
                branch_label_frame,
                height=20,
                width=30,
                text="X",
                fg_color=self.BRANCH_CANCEL_COLOR,
                hover_color=self.BRANCH_CANCEL_HOVER
            )

            confirm_button = ctk.CTkButton(
                branch_label_frame,
                height=20,
                width=30,
                text="✔",
                fg_color=self.BRANCH_CONFIRM_COLOR,
                hover_color=self.BRANCH_CONFIRM_HOVER
            )

            delete_branch_label = ctk.CTkLabel(
                branch_label_frame,
                font=("Arial", 12, "bold"),
                text="Confirm delete?",
                text_color="#FF6B6B"
            )

            branch_rename_button = ctk.CTkButton(
                branch_label_frame,
                width=50,
                height=20,
                text="rename",
                font=("Arial", 10),
                fg_color=self.BRANCH_BUTTON_COLOR,
                hover_color=self.BRANCH_BUTTON_HOVER,
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
                fg_color=self.BRANCH_BUTTON_COLOR,
                hover_color=self.BRANCH_BUTTON_HOVER,
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
                fg_color=self.BRANCH_MOVE_COLOR,
                hover_color=self.BRANCH_MOVE_HOVER,
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
                fg_color=self.BRANCH_MOVE_COLOR,
                hover_color=self.BRANCH_MOVE_HOVER,
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
                fg_color=self.BRANCH_DELETE_COLOR,
                hover_color=self.BRANCH_DELETE_HOVER,
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
                branch_row,
                orientation="horizontal",
                height=self.ROW_HEIGHT
            )

            row_frame.pack(
                side="left",
                fill="both",
                expand=True
            )

            for action_index, entry in enumerate(branch):

                is_active_branch = branch_id == self.history.current_branch
                is_current_action = (
                        is_active_branch
                        and action_index == self.history.current_action_index
                )

                if not is_active_branch:
                    # Entire inactive branch is muted
                    card_color = self.INACTIVE_BRANCH_COLOR
                    hover_color = self.INACTIVE_ACTION_HOVER
                    border_width = self.DEFAULT_ACTION_BORDER_WIDTH
                    border_color = self.INACTIVE_BRANCH_COLOR

                elif action_index < self.history.current_action_index:
                    # Operation has already been applied
                    card_color = self.COMPLETED_ACTION_COLOR
                    hover_color = self.COMPLETED_ACTION_HOVER
                    border_width = self.DEFAULT_ACTION_BORDER_WIDTH
                    border_color = self.COMPLETED_ACTION_COLOR

                elif is_current_action:
                    # Current dataset state
                    card_color = self.CURRENT_ACTION_COLOR
                    hover_color = self.CURRENT_ACTION_HOVER
                    border_width = self.CURRENT_ACTION_BORDER_WIDTH
                    border_color = self.CURRENT_ACTION_BORDER_COLOR

                else:
                    # Operation exists in history, but is after current state
                    card_color = self.FUTURE_ACTION_COLOR
                    hover_color = self.FUTURE_ACTION_HOVER
                    border_width = self.DEFAULT_ACTION_BORDER_WIDTH
                    border_color = self.FUTURE_ACTION_COLOR

                card = ctk.CTkButton(
                    row_frame,
                    width=240,
                    height=self.ROW_HEIGHT,

                    fg_color=card_color,
                    hover_color=hover_color,

                    border_width=border_width,
                    border_color=border_color,

                    text=(
                        f"{entry['name']}\n\n"
                        f"{entry['desc']}\n\n"
                        f"{format_args(entry['args'])}"
                    ),

                    command = lambda
                        act_id=action_index,
                        br_id=branch_id:
                    self.select_action(br_id, act_id)
                )

                card.pack(
                    side="left",
                    padx=5,
                )

        add_branch_button = ctk.CTkButton(
            self.main_frame,
            text="+",
            width=50,
            height=50,
            font=("Arial", 30, "bold"),
            command=self.create_branch,
            fg_color=self.BRANCH_MOVE_COLOR
        )

        add_branch_button.pack(
            pady=10
        )