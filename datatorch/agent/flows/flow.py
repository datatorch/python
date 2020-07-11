import os
import yaml
import logging

from typing import List, Union
from .job import Job


logger = logging.getLogger("datatorch.agent.flow")


class Flow(object):
    @classmethod
    def from_yaml(cls, path, agent=None):
        with open(path, "r") as config_file:
            config = yaml.load(config_file, Loader=yaml.FullLoader)
        config["name"] = config.get("name", os.path.splitext(os.path.basename(path))[0])
        return cls.from_config(config, agent)

    @classmethod
    def from_config(cls, config: Union[str, dict], agent=None):

        if isinstance(config, str):
            config = yaml.load(config, Loader=yaml.FullLoader)

        return Flow(config, agent=agent)

    def __init__(self, config: dict, agent=None):
        self.name = config.get("name")
        self.config = config

    async def run(self, job_config: dict):
        """ Runs a job. """
        await Job(job_config, agent=self.agent).run()
