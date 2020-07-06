import logging

from typing import List
from .step import Step


logger = logging.getLogger(__name__)


def _dict_to_job(name: str, config: dict):
    assert "steps" in config, "A job must have steps."
    assert len(config["steps"]) != 0, "A job must have steps."
    steps = Step.from_dict_list(config["steps"])
    return Job(name, steps)


class Job(object):
    @classmethod
    def from_dict(cls, config: dict):
        return [_dict_to_job(k, v) for k, v in config.items()]

    def __init__(self, name, steps: List[Step]):
        self.current_step = 0
        self.name = name

        self.steps = steps

    def __iter__(self) -> Step:
        return self.steps[self.current_step]

    def __next__(self) -> Step:
        if self.current_step < len(self.steps):
            self.current_step += 1
            return self.__iter__()
        else:
            raise StopIteration

    def run(self):
        inputs = []
        for step in self.steps:
            try:
                inputs = step.run(inputs)
            except (ValueError, SyntaxError) as e:
                logger.error(e)
                break
        else:
            logger.success("Successfully completed job.")
