import pandas as pd
import numpy as np

class HistoryManager:
    def __init__(self, imputation_manager):
        self.branches = [[]]
        self.current_branch = 0
        self.current_action_index = 0
        self.imputation_manager = imputation_manager

        self.branch_names = []

    def register_view_update_callback(self, update_callback):
        self.imputation_manager.register_update_callback(update_callback)

    def clear_history(self):
        self.branches = [[]]
        self.current_branch = 0
        self.current_action_index = 0
        self.branch_names = ["Main"]

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

    def rename_branch(self, branch_id, branch_name):
        self.branch_names[branch_id] = branch_name
        self.imputation_manager.save_app_data()

    def swap_branches(self, branch1_id, branch2_id):
        if self.current_branch == branch1_id:
            self.current_branch = branch2_id
        elif self.current_branch == branch2_id:
            self.current_branch = branch1_id

        self.branches[branch1_id], self.branches[branch2_id] = self.branches[branch2_id], self.branches[branch1_id]
        self.branch_names[branch1_id], self.branch_names[branch2_id] = self.branch_names[branch2_id], self.branch_names[branch1_id]
        self.imputation_manager.save_app_data()

    def get_current_history(self):
        return self.get_history_branch(self.current_branch)

    def get_history_branch(self, branch_id):
        return self.branches[branch_id]

    def create_branch_from(self, branch_id, index = -1, name = ""):
        """Creates new branch with operations until index."""
        if index == -1:
            index = self.current_action_index
        base_ops = self.branches[branch_id][:index+1]
        if name == "":
            name = self.branch_names[branch_id]+"_copy"
        new_branch = [op.copy() for op in base_ops]
        self.branches.insert(branch_id+1,new_branch)
        self.branch_names.insert(branch_id+1,name)
        self.current_branch = branch_id+1
        self.current_action_index = len(self.branches[self.current_branch]) - 1
        self.select_action(self.current_branch, self.current_action_index, True)

    def select_action(self, branch_id, action_id, force = False):
        if branch_id == self.current_branch and action_id == self.current_action_index and not force:
            return False
        self.current_action_index = action_id
        self.current_branch = branch_id
        self.imputation_manager.load_dataset_state(self.current_branch, self.current_action_index)
        return True

    def create_new_branch(self):
        if len(self.branches) == 0:
            self.branch_names.append("Main")
        else:
            self.branch_names.append("Branch "+str(len(self.branches)+1))
        self.branches.append([])

        self.current_branch = len(self.branches)-1
        self.imputation_manager.load_dataset_action()
        self.current_action_index = 0
        self.select_action(self.current_branch, self.current_action_index, True)

    def delete_branch(self, branch_id):
        if len(self.branches) == 1 and branch_id == self.current_branch:
            self.branches.clear()
            self.branch_names.clear()
            self.current_branch = 0
            self.current_action_index = 0
            self.create_new_branch()
            return
        if branch_id == self.current_branch and branch_id == len(self.branches)-1:
            self.current_branch = len(self.branches)-2
            self.current_action_index = len(self.branches[self.current_branch]) - 1

        self.branches.remove(self.branches[branch_id])
        self.branch_names.remove(self.branch_names[branch_id])
        self.select_action(self.current_branch, self.current_action_index, True)

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

        if not isinstance(branches, list) or not branches:
            raise ValueError("History must contain at least one branch.")

        if not isinstance(branch_names, list):
            raise ValueError("Invalid branch names.")

        if len(branch_names) != len(branches):
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
        self.current_branch = current_branch
        self.current_action_index = current_action_index



