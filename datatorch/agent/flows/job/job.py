import logging
import asyncio

from typing import List
from ..step import Step


logger = logging.getLogger("datatorch.agent.job")


STEP_TIMEOUT = 60 * 60 * 24 * 5  # 5 days


def _dict_to_job(name: str, config: dict, agent=None):
    assert "steps" in config, "A job must have steps."
    assert len(config["steps"]) != 0, "A job must have steps."
    steps = Step.from_dict_list(config["steps"], agent)
    return Job(name, steps, agent)


class Job(object):
    @classmethod
    def from_dict(cls, config: dict, agent=None):
        return [_dict_to_job(k, v, agent) for k, v in config.items()]

    def __init__(self, name, steps: List[Step], agent=None):
        self.current_step = 0
        self.name = name
        self.steps = steps
        self.agent = agent

    async def run(self):
        inputs = []
        for step in self.steps:
            try:
                inputs = await asyncio.wait_for(step.run(inputs), timeout=STEP_TIMEOUT)
            except (ValueError, SyntaxError) as e:
                logger.error(e)
                break
        else:
            logger.info("Successfully completed job.")
