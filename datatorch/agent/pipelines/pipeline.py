import os
import yaml
import logging

from typing import Union, TYPE_CHECKING


if TYPE_CHECKING:
    from ..agent import Agent


logger = logging.getLogger("datatorch.agent.pipeline")


class Pipeline(object):
    @classmethod
    def from_yaml(cls, path, agent: "Agent" = None):
        with open(path, "r") as config_file:
            config = yaml.load(config_file, Loader=yaml.FullLoader)
        config["name"] = config.get("name", os.path.splitext(os.path.basename(path))[0])
        return cls.from_config(config, agent)

    @classmethod
    def from_config(cls, config: Union[str, dict], agent: "Agent" = None):
        """ Creates a pipeline from a config file. """
        if isinstance(config, str):
            cf = yaml.load(config, Loader=yaml.FullLoader)
        else:
            cf = config
        return cls(cf, agent=agent)

    def __init__(self, config: dict, agent: "Agent" = None):
        self.name = config.get("name")
        self.config = config
        self.agent = agent

    async def run(self, job_config: dict):
        """ Runs a job. """
        # await Job(job_config, agent=self.agent).run()
        pass
