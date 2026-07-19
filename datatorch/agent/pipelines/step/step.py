from datatorch.utils.objects import pick
from datatorch.agent.pipelines.action.config import ActionConfig
import logging
from typing import List, Optional
from datetime import datetime, timezone
from ..action import get_action, Action
from ..template import Variables
from typing import TYPE_CHECKING, Union
import asyncio

if TYPE_CHECKING:
    from ...client import AgentApiClient, AgentStepDispatch, Log


UPLOAD_LOGS_EVERY_SECONDS = 10


class Step(object):
    """
    A single executable step. Server mode builds it from an
    AgentStepDispatch (inputs already server-resolved); local mode builds
    it from the yaml config (inputs resolved by pipelines.resolver).
    Status reporting (claim/complete) is the caller's job — the step only
    executes and uploads logs.
    """

    @classmethod
    def from_dispatch(cls, dispatch: "AgentStepDispatch", api: "AgentApiClient" = None):
        return cls(
            id=dispatch.get("stepId"),
            action=dispatch.get("action", ""),
            name=dispatch.get("stepName") or "",
            inputs=dispatch.get("input") or {},
            run_id=dispatch.get("runId"),
            api=api,
        )

    @classmethod
    def from_dict(cls, step: dict, api: "AgentApiClient" = None):
        return cls(
            id=step.get("id"),
            cacheable=step.get("cache", None),
            action=step.get("action", ""),
            name=step.get("name", ""),
            inputs=step.get("inputs", {}),
            api=api,
        )

    def __init__(
        self,
        id: str = None,
        action: Union[str, dict] = "",
        name: str = "",
        cacheable: Union[bool, None] = None,
        inputs: dict = {},
        run_id: str = None,
        api: "AgentApiClient" = None,
    ):
        self._action = ActionConfig(action)
        self.id = id
        self.logs: "List[Log]" = []
        self.name = name
        self.inputs = inputs
        self.cacheable = cacheable
        self.run_id = run_id
        self.api = api
        self.rendered_inputs: Optional[dict] = None
        self.logger = logging.getLogger(f"datatorch.agent.[{self._action.full_name}]")

    async def action(self) -> Action:
        return await get_action(self._action, step=self)

    async def run(self, variables: Variables) -> dict:
        # Upload logs in the background.
        task = asyncio.create_task(self.log_uploader())

        variables.set_step(self)

        # Seed the step's own inputs into the action-local `input`
        # namespace (rendering machine-local template refs).
        for k, v in self.inputs.items():
            variables.add_input(k, v)

        try:
            action = await self.action()
            outputs = await action.run(variables)
        finally:
            task.cancel()

        # What actually ran: the inputs after machine-local rendering and
        # the action's default/required/type-cast pass. Echoed to the
        # server on completion.
        self.rendered_inputs = pick(
            variables.inputs.copy(),
            list({**action.inputs, **self.inputs}.keys()),
        )

        await self.upload_logs()
        return outputs

    async def log_uploader(self):
        await asyncio.sleep(UPLOAD_LOGS_EVERY_SECONDS)
        await self.upload_logs()

    def log(self, message: str):
        """Records a log message."""
        iso_date = datetime.now(timezone.utc).isoformat()[:-9] + "Z"
        self.logs.append(dict(createdAt=iso_date, message=message))  # type: ignore
        self.logger.info(message)

    async def upload_logs(self):
        """Uploads saved logs to webserver."""
        if self.api and self.id and len(self.logs) > 0:
            logs = self.logs
            self.logs = []
            await self.api.upload_step_logs(self.id, logs)
