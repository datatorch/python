import os
import logging
import subprocess
import asyncio

from .....template import render


logger = logging.getLogger(__name__)


class Runner(object):
    def __init__(self, config, action):
        self.config = config
        self.action = action
        self.inputs = {}
        self.original_wd = os.getcwd()

    def run(self, agent, inputs={}):
        """ Setups and excutes runner. """
        self.agent = None
        self.inputs = inputs
        self.execute()
        self.inputs = {}

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

    def run_cmd_async(self, command: str):
        return subprocess.run(command, shell=True, stdout=subprocess.PIPE)

    def get(self, key, default=None):
        """ Gets a string from config and renders templating. """
        return self.template(self.config.get(key, default), self.inputs)

    def template(self, string, variables={}) -> str:
        return render(string, variables or {})
