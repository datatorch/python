from typing import List
from .action import get_action


def _dict_to_step(self, config: dict):
    pass


class Step(object):
    @classmethod
    def from_dict_list(cls, steps: List[dict]):
        return [cls.from_dict(s) for s in steps]

    @classmethod
    def from_dict(cls, step: dict):
        return cls(
            action_string=step.get("action"),
            name=step.get("name"),
            inputs=step.get("inputs", []),
        )

    def __init__(self, action_string: str = None, name: str = "", inputs=[]):
        self._action_string = action_string
        self.name = name
        self.inputs = inputs

    def action(self):
        return get_action(self._action_string)

    def run(self, inputs=[]):
        if self.run:
            action = None
            # cmd action
        else:
            action = get_action(self.action)
        return self.action.run(inputs)
