import os
import yaml
import logging

from typing import List
from .runner import RunnerFactory
from .....directory import AgentDirectory


logger = logging.getLogger(__name__)


class ActionValidator(Exception):
    pass


class Action(object):
    def __init__(self, action: str, directory: str):
        name, version = action.split("@", 1)

        self.dir = directory
        self.config_path = os.path.join(self.dir, "config.yaml")
        self.config = self._load_config()

        self.version = version
        self.name = self.config.get("name", name)
        self.description = self.config.get("description", "")
        self.inputs = self.config.get("inputs", [])
        self.outputs = self.config.get("outputs", [])

        runs = self.config.get("runs", None)
        if runs is None:
            raise ActionValidator("Action must have a run section.")

        self.runner = RunnerFactory.create(self, runs)

    def _load_config(self):
        with open(self.config_path, "r") as config_file:
            return yaml.load(config_file, Loader=yaml.FullLoader)

    def run(self, agent, inputs):
        self.runner.execute()
