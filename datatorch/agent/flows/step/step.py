from typing import List, Awaitable
from ..action import get_action, Action
from ..template import render


def _dict_to_step(self, config: dict):
    pass


class Step(object):
    @classmethod
    def from_dict_list(cls, steps: List[dict], agent=None):
        return [cls.from_dict(s, agent) for s in steps]

    @classmethod
    def from_dict(cls, step: dict, agent=None):
        return cls(
            action_string=step.get("action"),
            name=step.get("name"),
            inputs=step.get("inputs", {}),
            agent=agent,
        )

    def __init__(
        self, action_string: str = None, name: str = "", inputs=[], agent=None
    ):
        self._action_string = action_string
        self.name = name
        self.inputs = inputs
        self.agent = agent

    async def action(self) -> Action:
        return await get_action(self._action_string, agent=self.agent)

    async def run(self, inputs: dict = {}) -> dict:

        # Add specified inputs
        for k, v in self.inputs.items():
            if isinstance(v, str):
                inputs[k] = render(v, {"variable": inputs})
            else:
                inputs[k] = v

        action = await self.action()
        output = await action.run(inputs)

        return output
