import os
import subprocess


class Runner(object):
    def __init__(self, action):
        self.action = action
        self.original_wd = os.getcwd()

    def execute(self):
        raise NotImplementedError("This method must be implemented.")

    def action_dir(self):
        """ Changes the current work directory to the actions directory. """
        os.chdir(self.action.dir)

    def original_dir(self):
        """ Changes the current work directory back to the original. """
        os.chdir(self.original_wd)

    def run_cmd(self, command: str):
        return subprocess.run(command, shell=True, stdout=subprocess.PIPE)
