import pandas as pd


class HistoryManager:
    def __init__(self):
        self.branches = [[]]
        self.current_branch = 0
        self.current_branch_id = 0

        self.branch_names = []

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
            index = self.current_branch_id
        base_ops = self.branches[branch_id][:index+1]
        if name == "":
            name = self.branch_names[branch_id]+"_copy"
        new_branch = [op.copy() for op in base_ops]
        self.branches.insert(branch_id+1,new_branch)
        self.branch_names.insert(branch_id+1,name)

    def create_new_branch(self):
        pass

    def delete_branch(self, branch_id):
        if len(self.branches) == 1 and branch_id == self.current_branch:
            self.branches.clear()
            self.branch_names.clear()
            self.current_branch = 0
            self.current_branch_id = 0
            self.create_new_branch()
            return
        if branch_id == self.current_branch and branch_id == len(self.branches)-1:
            self.current_branch = len(self.branches)-2
            self.current_branch_id = len(self.branches[self.current_branch])-1

        self.branches.remove(self.branches[branch_id])
        self.branch_names.remove(self.branch_names[branch_id])

    def revert_to(self, index, original_df):
        """Reverts branch to a previous state by re-performing operations."""
        df = original_df.copy(deep=True)
        ops = self.branches[self.current_branch][:index+1]

        for op in ops:
            df = self.apply_operation(df, op)

        return df

    def apply_operation(self, df, op):
        """Performs operation on df."""
        action = op["action"]
        args = op["args"]

        if action == "impute":
            return self._apply_imputation(df, args)
        elif action == "drop_columns":
            return df.drop(columns=args["columns"])
        elif action == "filter":
            return df.query(args["query"])
        elif action == "missingness":
            return self._apply_missingness(df, args)

        return df


