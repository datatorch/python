from typing import List
from datetime import datetime, timezone
from ..action import get_action, Action
from ..template import render

import copy


def _pick(dic: dict, keys: List[str]):
    return {key: dic[key] for key in keys}


class Step(object):
    @classmethod
    def from_dict_list(cls, steps: List[dict], agent=None):
        return [cls.from_dict(s, agent) for s in steps]

    @classmethod
    def from_dict(cls, step: dict, agent=None):
        return cls(
            id=step.get("id"),
            action_string=step.get("action"),
            name=step.get("name"),
            inputs=step.get("inputs", {}),
            agent=agent,
        )

    def __init__(
        self,
        id: str = None,
        action_string: str = None,
        name: str = "",
        inputs: dict = {},
        agent=None,
    ):
        self._action_string = action_string
        self.id = id
        self.name = name
        self.inputs = inputs
        self.agent = agent

    async def action(self) -> Action:
        return await get_action(self._action_string, agent=self.agent)

    async def update(
        self, inputs: dict = None, status: str = None, outputs: dict = None
    ):
        if self.agent is None and self.id is None:
            return

        if inputs is not None:
            inputs = _pick(inputs.copy(), self.inputs.keys())

        iso_date = datetime.now(timezone.utc).isoformat()[:-9] + "Z"
        variables = {
            "id": self.id,
            "inputs": inputs,
            "outputs": outputs,
            "status": status,
            "startedAt": iso_date if status == "RUNNING" else None,
            "finishedAt": iso_date if status == "COMPLETED" else None,
        }
        await self.agent.api.update_step(variables)

    async def run(self, inputs: dict = {}) -> dict:

        # Add specified inputs
        for k, v in self.inputs.items():
            # If input is a string, render any variables
            inputs[k] = render(v, {"variable": inputs}) if isinstance(v, str) else v

        # Outputs will be updated by the action as it casts them into the
        # correct format.
        await self.update(status="RUNNING")

        action = await self.action()
        outputs = await action.run(inputs, self)

        await self.update(outputs=outputs, status="COMPLETED")

        return outputs
