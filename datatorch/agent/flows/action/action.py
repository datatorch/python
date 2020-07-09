import os
import yaml
import logging

from ..runner import RunnerFactory


logger = logging.getLogger("datatorch.agent.action")


class Action(object):
    def __init__(self, action: str, directory: str, agent=None):
        name, version = action.split("@", 1)

        self.dir = directory
        self.identifier = action
        self.config_path = os.path.join(self.dir, "config.yaml")
        self.config = self._load_config()

        self.version = version
        self.agent = agent
        self.name = self.config.get("name", name)
        self.description = self.config.get("description", "")
        self.inputs = self.config.get("inputs", [])
        self.outputs = self.config.get("outputs", [])

        runs = self.config.get("runs", None)
        if runs is None:
            raise ValueError("Action must have a run section.")

        self.runner = RunnerFactory.create(self, runs)
        self.logger = logging.getLogger(
            "datatorch.agent.action.{}".format(self.identifier)
        )

    def _load_config(self):
        with open(self.config_path, "r") as config_file:
            return yaml.load(config_file, Loader=yaml.FullLoader)

    async def run(self, agent, inputs):
        logger.info("Running action {}".format(self.identifier))
        await self.runner.run(agent, inputs)
        logger.debug("Finished running '{}' v{}".format(self.name, self.version))

    @property
    def full_name(self):
        return "{}@{}".format(self.name, self.version)
