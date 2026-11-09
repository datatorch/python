import os
import logging
import asyncio

from typing import Awaitable, Callable, Dict, List, Optional
from .client import AgentApiClient, AgentStepDispatch, is_transient
from .pipelines.template import Variables
from .log_handler import AgentAPIHandler
from .monitoring import AgentSystemStats
from .directory import runner_directory

from gql.client import AsyncClientSession
from datatorch.runner.pipelines.step import Step

logger = logging.getLogger(__name__)

# Every task the daemon spawned that is still running: step tasks and the
# per-connection service tasks (monitoring, the cancel and command
# listeners). A task removes itself when it finishes, so the list counts
# what is really in flight. Before 0.8.3 it only ever grew (the prod runner
# logged "Exiting 71 active jobs", then 74, then 77 across three reconnects
# on 2026-11-09).
tasks: List[asyncio.Task] = []

# A finished step's result (its last log batch and the completion
# mutation) is retried across a lost connection for this long; after that
# the runner logs the loss and drops the result. The server fails a
# RUNNING step once its runner has been unseen for about two minutes, so a
# much longer outage has already decided the step's fate there.
REPORT_DEADLINE_SECONDS = 600
# Pause between two attempts while connected (the socket may be up but the
# call still failing, e.g. the API pod is restarting behind it).
REPORT_RETRY_SECONDS = 5
# One attempt may not sit on a half-open socket for longer than this.
REPORT_CALL_TIMEOUT_SECONDS = 60


def _track(task: asyncio.Task) -> asyncio.Task:
    tasks.append(task)
    task.add_done_callback(_untrack)
    return task


def _untrack(task: asyncio.Task) -> None:
    try:
        tasks.remove(task)
    except ValueError:
        pass


class RunnerDaemon(object):
    """
    Runner protocol v2: the server sequences steps. The runner receives one
    ready step at a time — its inputs already resolved server-side —
    claims it, executes it, and reports the result. Job-level state and
    cross-step dataflow live entirely on the server.

    One daemon lives for the whole process and outlives the websocket:
    `serve(session)` runs one connection's worth of work (recover pending
    steps, listen for pushes, monitor) and returns or raises when that
    connection ends. Running steps belong to the daemon, not to the
    connection, so a dropped socket leaves them running; they report
    through whichever session is attached when they finish (`_report`).
    """

    @classmethod
    async def run(cls, session):
        """One connection, one daemon (the pre-0.8.3 shape, kept for
        callers outside this package). `runner.start` keeps a single
        daemon across reconnects instead."""
        daemon = cls()
        await daemon.serve(session)

    def __init__(self, api: Optional[AgentApiClient] = None):
        self.api = api or AgentApiClient()
        self.directory = runner_directory
        # Running step tasks, keyed by stepId, so a server cancel/timeout
        # signal can abort the right one. Entries are cleaned up when the
        # step finishes.
        self._step_tasks: Dict[str, asyncio.Task] = {}
        # Tasks that live only as long as the current connection.
        self._service_tasks: List[asyncio.Task] = []
        self.system_stats: Optional[AgentSystemStats] = None
        logger.debug(f"Switch to agent directory: {self.directory.dir}")
        os.chdir(self.directory.dir)

        self._init_logger()

    def _init_logger(self):
        self.logger = logging.getLogger("datatorch.runner")
        self.logger_api_handler = AgentAPIHandler(self.api)
        self.logger.addHandler(self.logger_api_handler)
        self.logger.debug("Runner logger has been initialized.")

    # -- connection lifecycle -------------------------------------------

    async def serve(self, session: AsyncClientSession):
        """Works one connection until it ends.

        Attaches the session (steps finishing now report through it),
        starts the per-connection services, then runs the dispatch loop.
        However the loop ends, the services are stopped and the API is
        detached; running steps are left alone."""
        self.api.attach(session)
        try:
            self._start_services()
            await self.process_loop()
        finally:
            self.disconnect()

    def disconnect(self) -> None:
        """The connection is gone (or being closed).

        Refuses API calls until the next `serve` attaches a session and
        cancels the per-connection services. Running steps are NOT
        cancelled: a websocket blip is not a reason to kill a four-hour
        step. Idempotent."""
        self.api.detach()
        for task in self._service_tasks:
            if not task.done():
                task.cancel()
        self._service_tasks = []

    def running_steps(self) -> List[asyncio.Task]:
        """The step tasks still in flight."""
        return [task for task in self._step_tasks.values() if not task.done()]

    def _service(self, coro) -> asyncio.Task:
        loop = asyncio.get_running_loop()
        task = _track(loop.create_task(coro))
        self._service_tasks.append(task)
        return task

    def _start_services(self):
        self.system_stats = AgentSystemStats(self)
        self._service(self.system_stats.start())

    # -- dispatch -------------------------------------------------------

    async def process_loop(self):
        """Drains steps missed while offline, then waits for pushes.

        Runs the dispatch stream alongside a cancel-signal listener: the
        server pushes a stop signal when a running step is canceled or
        times out, and the agent aborts that step's task.
        """
        pending = await self.api.pending_steps()
        if pending:
            logger.info(f"Recovered {len(pending)} pending step(s) on connect.")
        for dispatch in pending:
            self._start_step(dispatch)

        logger.info("Waiting for steps.")
        cancel_task = self._service(self._cancel_loop())
        command_task = self._service(self._command_loop())
        try:
            async for request in self.api.agent_steps():
                self._start_step(request.get("step"))
        finally:
            cancel_task.cancel()
            command_task.cancel()

    async def _command_loop(self):
        """Answers the server's requests about this runner's own action
        folders (read or write `actions/local/<name>/<tag>`). Nothing
        outside those folders is ever read or written: the directory
        refuses any other path. A failure is the answer's error, never a
        crash of the loop."""
        try:
            async for request in self.api.runner_commands():
                command = request.get("command") or {}
                self._service(self._answer_command(command))
        except asyncio.CancelledError:
            raise
        except Exception as ex:
            # A server from before runner commands has no such subscription;
            # steps still flow, only editing from DataTorch is off.
            logger.warning(f"Runner commands are not available: {ex}")

    async def _answer_command(self, command: dict):
        command_id = command.get("id")
        kind = command.get("kind")
        payload = command.get("payload") or {}
        result, error = None, None
        try:
            name, tag = payload.get("name"), payload.get("tag")
            if kind == "READ_LOCAL_ACTION":
                result = {"files": runner_directory.local_action_files(name, tag)}
            elif kind == "WRITE_LOCAL_ACTION":
                files = runner_directory.write_local_action_files(
                    name, tag, payload.get("files") or [], payload.get("delete") or []
                )
                result = {"files": files}
                logger.info(f"Wrote actions/local/{name}/{tag} on request.")
                # Report the folder's yaml now, so the picker lists it at once.
                try:
                    await self.api.report_local_actions(
                        runner_directory.local_actions()
                    )
                except Exception as ex:
                    logger.warning(
                        f"Could not report local actions after a write: {ex}"
                    )
            else:
                error = f"Unknown runner command '{kind}'."
        except (ValueError, FileNotFoundError, OSError) as ex:
            error = str(ex)
        except Exception as ex:  # the loop must survive anything
            logger.exception("Runner command failed.")
            error = f"{type(ex).__name__}: {ex}"
        try:
            await self.api.complete_runner_command(
                command_id, result=result, error=error
            )
        except Exception as ex:
            logger.warning(f"Could not answer runner command {command_id}: {ex}")

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
        step_id = dispatch.get("stepId")
        running = self._step_tasks.get(step_id)
        if running and not running.done():
            # A second push for a step this process already works on (a
            # dispatch repeated across a reconnect). The claim would be
            # refused anyway; don't start a second task for it.
            logger.debug(f"Step {step_id} is already running here; push ignored.")
            return
        loop = asyncio.get_running_loop()
        task = _track(loop.create_task(self._run_step(dispatch)))
        self._step_tasks[step_id] = task

    async def _run_step(self, dispatch: AgentStepDispatch):
        """Claims and executes a single dispatched step."""
        step_id = dispatch.get("stepId")
        step_name = dispatch.get("stepName") or dispatch.get("action")

        try:
            try:
                claimed = await self.api.claim_step(step_id)
            except Exception as e:
                # The connection went before the claim got through. The
                # step stays QUEUED on the server and comes back through
                # `pending_steps` on reconnect (or the reconciler
                # re-drives it), so nothing is lost by stopping here.
                logger.warning(
                    f"Could not claim step {step_id} ({e}); "
                    "it is offered again on reconnect."
                )
                return
            if not claimed:
                # Another process (or an earlier duplicate dispatch) owns it.
                logger.debug(f"Step {step_id} already claimed; skipping.")
                return

            logger.info(f"Step received (name: {step_name}, id: {step_id})")
            step = Step.from_dispatch(dispatch, api=self.api)

            try:
                outputs = await step.run(Variables())
            except asyncio.CancelledError:
                # A server stop signal (the step is already terminal
                # server-side) or a real shutdown of this runner: the child
                # process was killed, so don't report a result. The last
                # log lines are best effort: the connection may be the very
                # thing that is gone.
                logger.info(f"Step {step_id} aborted.")
                try:
                    await step.upload_logs()
                except Exception:
                    pass
                raise
            except Exception as e:
                error_message = str(e)
                logger.error(f"Step {step_id} failed: {error_message}")
                step.log(f"Step failed: {error_message}.")
                await self._report(
                    step,
                    lambda: self.api.complete_step(
                        step_id, success=False, error_message=error_message
                    ),
                )
                return

            reported = await self._report(
                step,
                lambda: self.api.complete_step(
                    step_id,
                    success=True,
                    output=outputs,
                    rendered_input=step.rendered_inputs,
                ),
            )
            if reported:
                logger.info(f"Step finished (name: {step_name}, id: {step_id})")
        finally:
            self._step_tasks.pop(step_id, None)

    async def _report(self, step: Step, send: Callable[[], Awaitable[bool]]) -> bool:
        """Gets a finished step's result to the server, across an outage.

        Ships the step's remaining log lines, then the completion. While
        the runner is disconnected it waits for the next session; a call
        that fails because of the connection is retried. It gives up after
        `REPORT_DEADLINE_SECONDS`, logging the loss. Returns whether the
        server accepted the result: False also when the server had already
        moved the step terminal (failed by the reconciler while this runner
        was offline), which is logged and otherwise absorbed.
        """
        loop = asyncio.get_running_loop()
        deadline = loop.time() + REPORT_DEADLINE_SECONDS
        logs_sent = False
        waiting_logged = False
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                logger.error(
                    f"Step {step.id}: could not report its result within "
                    f"{REPORT_DEADLINE_SECONDS} seconds of finishing; the result "
                    "is dropped (the server fails a step whose runner stays "
                    "unseen, so it is not left hanging)."
                )
                return False
            if not self.api.connected:
                if not waiting_logged:
                    logger.warning(
                        f"Step {step.id} finished while disconnected; holding "
                        "its result until the connection is back."
                    )
                    waiting_logged = True
                await self.api.wait_connected(timeout=remaining)
                continue
            try:
                if not logs_sent:
                    await asyncio.wait_for(
                        step.upload_logs(), REPORT_CALL_TIMEOUT_SECONDS
                    )
                    logs_sent = True
                accepted = await asyncio.wait_for(send(), REPORT_CALL_TIMEOUT_SECONDS)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if not is_transient(e):
                    logger.error(f"Step {step.id}: the server refused the result: {e}")
                    return False
                logger.warning(f"Step {step.id}: reporting failed ({e}); retrying.")
                await asyncio.sleep(min(REPORT_RETRY_SECONDS, max(remaining, 0)))
                continue
            if not accepted:
                logger.warning(
                    f"Step {step.id}: the server did not accept the result; the "
                    "step was already terminal there (failed while this runner "
                    "was offline, canceled, or timed out)."
                )
            return bool(accepted)


# Pre-rename name, kept for callers outside this package.
Agent = RunnerDaemon
