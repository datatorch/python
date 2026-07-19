import os
import logging
import asyncio

from typing import Dict, List
from .client import AgentApiClient, AgentStepDispatch
from .pipelines.template import Variables
from .log_handler import AgentAPIHandler
from .monitoring import AgentSystemStats
from .directory import agent_directory

from gql.client import AsyncClientSession
from datatorch.agent.pipelines.step import Step

logger = logging.getLogger(__name__)
tasks: List[asyncio.Task] = []


class Agent(object):
    """
    Agent protocol v2: the server sequences steps. The agent receives one
    ready step at a time — its inputs already resolved server-side —
    claims it, executes it, and reports the result. Job-level state and
    cross-step dataflow live entirely on the server.
    """

    @classmethod
    async def run(cls, session):
        agent = cls(session)
        await agent.process_loop()

    def __init__(self, session: AsyncClientSession):
        self.api = AgentApiClient(session)
        self.directory = agent_directory
        # Running step tasks, keyed by stepId, so a server cancel/timeout
        # signal can abort the right one. Entries are cleaned up when the
        # step finishes.
        self._step_tasks: Dict[str, asyncio.Task] = {}
        logger.debug(f"Switch to agent directory: {self.directory.dir}")
        os.chdir(self.directory.dir)

        self._init_logger()
        self._init_threads()

    def _init_logger(self):
        self.logger = logging.getLogger("datatorch.agent")
        self.logger_api_handler = AgentAPIHandler(self.api)
        self.logger.addHandler(self.logger_api_handler)
        self.logger.debug("Agent logger has been initalized.")

    def _init_threads(self):
        self.system_stats = AgentSystemStats(self)
        loop = asyncio.get_running_loop()
        task = loop.create_task(self.system_stats.start())
        tasks.append(task)

    async def process_loop(self):
        """Drains steps missed while offline, then waits for pushes.

        Runs the dispatch stream alongside a cancel-signal listener: the
        server pushes a stop signal when a running step is canceled or
        times out, and the agent aborts that step's task.
        """
        loop = asyncio.get_running_loop()

        pending = await self.api.pending_steps()
        if pending:
            logger.info(f"Recovered {len(pending)} pending step(s) on connect.")
        for dispatch in pending:
            self._start_step(dispatch)

        logger.info("Waiting for steps.")
        cancel_task = loop.create_task(self._cancel_loop())
        tasks.append(cancel_task)
        try:
            async for request in self.api.agent_steps():
                self._start_step(request.get("step"))
        finally:
            cancel_task.cancel()

    async def _cancel_loop(self):
        """Aborts a running step's task when the server signals a stop."""
        async for request in self.api.agent_step_cancels():
            cancel = request.get("cancel") or {}
            step_id = cancel.get("stepId")
            task = self._step_tasks.get(step_id)
            if task and not task.done():
                logger.info(f"Received stop signal for step {step_id}.")
                task.cancel()
            else:
                # Unknown/finished step — the signal is best-effort and the
                # server has already moved the step terminal.
                logger.debug(f"Stop signal for step {step_id} ignored (not running).")

    def _start_step(self, dispatch: AgentStepDispatch):
        """Schedules a step and tracks its task for cancellation."""
        loop = asyncio.get_running_loop()
        step_id = dispatch.get("stepId")
        task = loop.create_task(self._run_step(dispatch))
        self._step_tasks[step_id] = task
        tasks.append(task)

    async def _run_step(self, dispatch: AgentStepDispatch):
        """Claims and executes a single dispatched step."""
        step_id = dispatch.get("stepId")
        step_name = dispatch.get("stepName") or dispatch.get("action")

        try:
            claimed = await self.api.claim_step(step_id)
            if not claimed:
                # Another process (or an earlier duplicate dispatch) owns it.
                logger.debug(f"Step {step_id} already claimed; skipping.")
                return

            logger.info(f"Step received (name: {step_name}, id: {step_id})")
            step = Step.from_dispatch(dispatch, api=self.api)

            try:
                outputs = await step.run(Variables())
            except asyncio.CancelledError:
                # Either a disconnect mid-step (the reconciler fails the
                # orphaned RUNNING step once the agent stays offline) or a
                # server stop signal (the step is already terminal
                # server-side). Either way the child process was killed by
                # the runner; don't report a result — a late completion
                # would be absorbed by the RUNNING guard anyway.
                logger.info(f"Step {step_id} aborted.")
                await step.upload_logs()
                raise
            except Exception as e:
                logger.error(f"Step {step_id} failed: {e}")
                step.log(f"Step failed: {e}.")
                await step.upload_logs()
                await self.api.complete_step(
                    step_id, success=False, error_message=str(e)
                )
                return

            await self.api.complete_step(
                step_id,
                success=True,
                output=outputs,
                rendered_input=step.rendered_inputs,
            )
            logger.info(f"Step finished (name: {step_name}, id: {step_id})")
        finally:
            self._step_tasks.pop(step_id, None)
