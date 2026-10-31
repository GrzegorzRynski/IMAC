import pandas as pd
import numpy as np

class HistoryManager:
    MISSINGNESS_ACTION_IDS = (1, 3)

    IMPUTATION_ACTION_ID_START = 4
    IMPUTATION_ACTION_ID_END = 99

    def __init__(self, imputation_manager):
        self.branches = [[]]
        self.current_branch = 0
        self.current_action_index = 0
        self.imputation_manager = imputation_manager

        self.branch_names = []
        self.branch_ids = []

        self.on_history_change_callbacks = []

    def register_view_update_callback(self, update_callback):
        self.imputation_manager.register_update_callback(update_callback)

    def register_history_update_callback(self, callback):
        if callback not in self.on_history_change_callbacks:
            self.on_history_change_callbacks.append(callback)

    def notify_history_change(self):
        for cb in self.on_history_change_callbacks:
            cb()

    def clear_history(self):
        self.branches = [[]]
        self.current_branch = 0
        self.current_action_index = 0
        self.branch_names = ["Main"]
        self.branch_ids = [0]

    def add_action(self, action_id, action_name, args, name, desc):
        entry = {
            "id": action_id,
            "action": action_name,
            "args": args,
            "name": name,
            "desc": desc,
            "timestamp": pd.Timestamp.now()
        }
        self.branches[self.current_branch] = self.branches[self.current_branch][:self.current_action_index+1]
        self.branches[self.current_branch].append(entry)
        if len(self.branches[self.current_branch]) > 1:
            self.current_action_index += 1

    def is_missingness_action(self, action_id):
        return action_id in self.MISSINGNESS_ACTION_IDS

    def is_imputation_action(self, action_id):
        return (
                self.IMPUTATION_ACTION_ID_START
                <= action_id
                <= self.IMPUTATION_ACTION_ID_END
        )

    def rename_branch(self, branch_index, branch_name):
        self.branch_names[branch_index] = branch_name
        self.imputation_manager.save_app_data()
        self.notify_history_change()

    def swap_branches(self, branch1_index, branch2_index):
        if self.current_branch == branch1_index:
            self.current_branch = branch2_index
        elif self.current_branch == branch2_index:
            self.current_branch = branch1_index

        self.branches[branch1_index], self.branches[branch2_index] = self.branches[branch2_index], self.branches[branch1_index]
        self.branch_names[branch1_index], self.branch_names[branch2_index] = self.branch_names[branch2_index], self.branch_names[branch1_index]
        self.branch_ids[branch1_index], self.branch_ids[branch2_index] = self.branch_ids[branch2_index], self.branch_ids[branch1_index]
        self.imputation_manager.save_app_data()
        self.notify_history_change()

    def get_current_history(self):
        return self.get_history_branch(self.current_branch)

    def get_history_branch(self, branch_index):
        if self.branches and len(self.branches) > branch_index:
            return self.branches[branch_index]
        return None

    def create_branch_from(self, branch_index, action_index = -1, name =""):
        """Creates new branch with operations until index."""
        if action_index == -1:
            action_index = len(self.branches[branch_index]) - 1
        base_ops = self.branches[branch_index][:action_index + 1]
        if name == "":
            name = self.branch_names[branch_index] + "_copy"
        new_branch = [op.copy() for op in base_ops]
        self.branches.insert(branch_index + 1, new_branch)
        self.branch_names.insert(branch_index + 1, name)
        self.current_branch = branch_index + 1

        new_branch_id = self.current_branch
        while new_branch_id in self.branch_ids:
            new_branch_id += 1
        self.branch_ids.insert(branch_index + 1, new_branch_id)

        self.current_action_index = len(self.branches[self.current_branch]) - 1
        self.select_action(self.current_branch, self.current_action_index, True)

    def select_action(self, branch_index, action_id, force = False):
        if branch_index == self.current_branch and action_id == self.current_action_index and not force:
            return False
        self.current_action_index = action_id
        self.current_branch = branch_index
        self.imputation_manager.load_dataset_state(self.current_branch, self.current_action_index)
        return True

    def create_new_branch(self):
        if len(self.branches) == 0:
            self.branch_names.append("Main")
        else:
            self.branch_names.append("Branch "+str(len(self.branches)+1))
        self.branches.append([])

        self.current_branch = len(self.branches)-1

        new_branch_id = self.current_branch
        while new_branch_id in self.branch_ids:
            new_branch_id += 1
        self.branch_ids.append(new_branch_id)

        self.imputation_manager.load_dataset_action()
        self.current_action_index = 0
        self.select_action(self.current_branch, self.current_action_index, True)

    def delete_branch(self, branch_index):
        del self.branches[branch_index]
        del self.branch_names[branch_index]
        del self.branch_ids[branch_index]

        if branch_index == self.current_branch:
            if len(self.branches) == 1:
                self.branches.clear()
                self.branch_names.clear()
                self.branch_ids.clear()
                self.current_branch = 0
                self.current_action_index = 0
                self.create_new_branch()
                return

            self.current_branch -= 1
            self.current_action_index = len(self.branches[self.current_branch]) - 1
            self.select_action(self.current_branch, self.current_action_index, True)
        else:
            self.notify_history_change()

    def save_history(self):

        def serialize_value(value):

            if isinstance(value, pd.Timestamp):
                return {
                    "__type__": "Timestamp",
                    "value": value.isoformat()
                }

            if isinstance(value, pd.Series):
                return {
                    "__type__": "Series",
                    "data": {
                        str(key): serialize_value(item)
                        for key, item in value.items()
                    },
                    "name": value.name
                }

            if isinstance(value, dict):
                return {
                    key: serialize_value(item)
                    for key, item in value.items()
                }

            if isinstance(value, (list, tuple)):
                return [
                    serialize_value(item)
                    for item in value
                ]

            if isinstance(value, np.generic):
                return serialize_value(value.item())

            if value is pd.NA:
                return None

            return value

        return {
            "branches": serialize_value(self.branches),
            "branch_names": self.branch_names.copy(),
            "branch_ids": self.branch_ids.copy(),
            "current_branch": self.current_branch,
            "current_action_index": self.current_action_index
        }

    def load_history(self, data):

        def deserialize_value(value):

            if isinstance(value, dict):

                value_type = value.get("__type__")

                if value_type == "Timestamp":
                    return pd.Timestamp(value["value"])

                if value_type == "Series":
                    series_data = {
                        key: deserialize_value(item)
                        for key, item in value["data"].items()
                    }

                    return pd.Series(
                        series_data,
                        name=value.get("name")
                    )

                return {
                    key: deserialize_value(item)
                    for key, item in value.items()
                }

            if isinstance(value, list):
                return [
                    deserialize_value(item)
                    for item in value
                ]

            return value

        if not isinstance(data, dict):
            raise ValueError("Invalid history data.")

        branches = data.get("branches")
        branch_names = data.get("branch_names")
        branch_ids = data.get("branch_ids")

        if not isinstance(branches, list) or not branches:
            raise ValueError("History must contain at least one branch.")

        if not isinstance(branch_names, list):
            raise ValueError("Invalid branch names.")

        if not isinstance(branch_ids, list):
            raise ValueError("Invalid branch ids.")

        if len(branch_names) != len(branches):
            raise ValueError("Branch names do not match branches.")

        if len(branch_ids) != len(branches):
            raise ValueError("Branch names do not match branches.")

        if not all(isinstance(branch, list) for branch in branches):
            raise ValueError("Invalid branch structure.")

        restored_branches = deserialize_value(branches)

        current_branch = data.get("current_branch", 0)
        current_action_index = data.get("current_action_index", 0)

        if type(current_branch) is not int or not 0 <= current_branch < len(branches):
            raise ValueError("Invalid current branch index.")

        if type(current_action_index) is not int:
            raise ValueError("Invalid current action index.")

        current_branch_actions = restored_branches[current_branch]

        if current_branch_actions:
            if not 0 <= current_action_index < len(current_branch_actions):
                raise ValueError("Invalid current action index.")
        elif current_action_index != 0:
            raise ValueError("Invalid action index for an empty branch.")

        self.branches = restored_branches
        self.branch_names = branch_names.copy()
        self.branch_ids = branch_ids.copy()
        self.current_branch = current_branch
        self.current_action_index = current_action_index



