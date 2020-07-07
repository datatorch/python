from typing import List
from ..action import get_action


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
            inputs=step.get("inputs", []),
            agent=agent,
        )

    def __init__(
        self, action_string: str = None, name: str = "", inputs=[], agent=None
    ):
        self._action_string = action_string
        self.name = name
        self.inputs = inputs
        self.agent = agent

    def action(self):
        return get_action(self._action_string, agent=self.agent)

    async def run(self, inputs=[]):
        """Runs a step with given imports.

        First downloads the action and then excutes it.

        Args:
            inputs (list, optional): actions input. Defaults to [].

        Returns:
            list: actions output
        """
        return await self.action().run(None, inputs)
