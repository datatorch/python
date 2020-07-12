import logging
import asyncio
import os
import yaml

from typing import List

from ...directory import agent_directory
from ..step import Step


logger = logging.getLogger("datatorch.agent.job")


class Job(object):
    def __init__(self, config: dict, agent=None):
        self.config = config
        self.agent = agent

        job_id = self.config.get("id")
        self.dir = agent_directory.task_dir(job_id) if job_id else "./"

        if job_id:
            path = os.path.join(self.dir, "job.yaml")
            with open(path, "w") as config:
                yaml.dump(self.config, config, default_flow_style=False)

    async def run(self):
        steps = Step.from_dict_list(self.config.get("steps"), agent=self.agent)
        inputs = {}
        for step in steps:
            try:
                inputs = {**inputs, **await step.run(inputs)}
            except Exception as e:
                logger.error(
                    f"Job {self.config.get('name')} {self.config.get('id')} failed: {e}"
                )
                await step.update(status="FAILED")
        else:
            logger.info("Successfully completed job.")
