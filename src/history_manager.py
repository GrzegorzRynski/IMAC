import pandas as pd


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
        self.branches[self.current_branch].append(entry)

    def rename_branch(self, branch_id, branch_name):
        self.branch_names[branch_id] = branch_name

    def swap_branches(self, branch1_id, branch2_id):
        if self.current_branch == branch1_id:
            self.current_branch = branch2_id
        elif self.current_branch == branch2_id:
            self.current_branch = branch1_id

        self.branches[branch1_id], self.branches[branch2_id] = self.branches[branch2_id], self.branches[branch1_id]
        self.branch_names[branch1_id], self.branch_names[branch2_id] = self.branch_names[branch2_id], self.branch_names[branch1_id]

    def get_current_history(self):
        return self.branches[self.current_branch]

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
        self.current_action_index = 0
        self.imputation_manager.load_dataset_action()
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





