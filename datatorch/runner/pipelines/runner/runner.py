import os
import json
import time
import signal
import typing
import asyncio

import psutil

from typing import Any, Awaitable, Dict
from ..template import Variables

if typing.TYPE_CHECKING:
    from ..action import Action


class ProcessCodeError(Exception):
    pass


# Max size of one stdout line from an action subprocess. Output values
# arrive as one `::var::<json>` line, so this bounds the largest single
# output value (e.g. an http-request body), not ordinary log lines.
STDOUT_LINE_LIMIT = 16 * 1024 * 1024

# How long a stopped step's processes get to exit by themselves (SIGTERM)
# before they are killed. The server has already closed the step by then,
# so nothing waits on this except the processes' own cleanup.
TERMINATE_GRACE_SECONDS = 5.0

# Windows has no process groups in this sense and no SIGKILL.
_POSIX = os.name == "posix"
_SIGKILL = getattr(signal, "SIGKILL", signal.SIGTERM)


def _descendants(pid: int) -> list:
    """Every process under `pid` right now, as psutil handles (which
    refuse to signal a pid that has since been reused)."""
    try:
        return psutil.Process(pid).children(recursive=True)
    except psutil.Error:
        return []


def _alive(proc) -> bool:
    try:
        return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except psutil.Error:
        return False


def _signal_tree(process, tree: list, sig: int) -> None:
    """Send `sig` to the step's process group and to every noted
    descendant, wherever it now lives. A process already gone is fine."""
    if process.returncode is None:
        try:
            if _POSIX:
                # run_cmd gives each step its own session, so its group id
                # is the shell's pid and never the runner's own group.
                os.killpg(process.pid, sig)
            else:
                process.send_signal(sig)
        except (ProcessLookupError, PermissionError, OSError):
            pass
    for proc in tree:
        try:
            proc.send_signal(sig)
        except (psutil.Error, OSError):
            pass


class Runner(object):
    def __init__(self, config: dict, action: "Action"):
        self.config = config
        self.action = action
        self.outputs: Dict[str, Any] = {}

    async def run(self, variables: Variables):
        self.variables = variables
        self.outputs = {}
        await self.execute()
        return self.outputs

    async def execute(self) -> Awaitable[dict]:
        raise NotImplementedError("This method must be implemented.")

    def action_dir(self):
        """Changes the current work directory to the actions directory."""
        os.chdir(self.action.dir)

    async def monitor_cmd(self, command: str, env: dict = None):
        """Executes a command and monitors stdout for variables and logging.

        Streams stdout live (rather than waiting then draining) so that if
        the step is canceled or times out server-side — the asyncio task
        running it receives ``CancelledError`` — the child process and
        everything it started are stopped instead of being orphaned.
        """
        process = await self.run_cmd(command, wait=False, env=env)

        try:
            async for log in process.stdout:
                log = log.decode("utf-8")
                self.check_for_output(log)
                self.log(log)
            await process.wait()
        except asyncio.CancelledError:
            await self._terminate(process)
            raise
        finally:
            # Abnormal exit (exception mid-stream) left the child running.
            if process.returncode is None:
                await self._terminate(process)

        if process.returncode != 0:
            raise ProcessCodeError(
                f"Process failed with exit code {process.returncode}"
            )

    async def _terminate(self, process):
        """Stop a still-running step: the whole process tree, not only the
        shell that wraps the command (best effort).

        `run_cmd` starts the command through a shell, so `process` is that
        shell. Killing it alone left everything under it running: on
        2026-11-11 a timed-out seed step's `claude` process worked on for
        40 minutes after the server had closed the step. So: note every
        descendant first (a process that moved to its own group is found by
        parentage, and once its parent dies that link is gone), ask the
        tree to stop with SIGTERM so a process that manages children of its
        own can stop them, then kill whatever is left after
        `TERMINATE_GRACE_SECONDS`.
        """
        if process.returncode is not None:
            return

        tree = _descendants(process.pid)
        _signal_tree(process, tree, signal.SIGTERM)

        deadline = time.monotonic() + TERMINATE_GRACE_SECONDS
        while time.monotonic() < deadline:
            if process.returncode is not None and not any(
                _alive(proc) for proc in tree
            ):
                break
            await asyncio.sleep(0.1)
        else:
            _signal_tree(process, tree, _SIGKILL)

        try:
            await process.wait()
        except ProcessLookupError:
            pass

    def get(self, key: str, default=None):
        """Gets a string from config and renders template."""
        return self.variables.render(self.config.get(key, default))

    def get_command(self, key: str, default=None):
        """Renders a shell command/script field: machine-local namespaces
        only, ${{ input.* }} forbidden (injection policy — inputs arrive as
        $INPUT_<NAME> via `input_env`)."""
        return self.variables.render_command(self.config.get(key, default))

    def runner_env(self) -> dict:
        """What an action needs to reach the server this runner is on:
        the API url and the runner's own token (as DATATORCH_API_URL and
        DATATORCH_RUNNER_TOKEN), and where the step sits in the record
        (DATATORCH_PROJECT_ID, DATATORCH_RUN_ID, DATATORCH_PIPELINE_ID,
        DATATORCH_STEP_ID). The SDK's client picks them up, so an
        action talks to the same server as the runner, as the runner,
        instead of the machine's stored login. Anything already set in
        the environment wins (DATATORCH_API_KEY included, since the SDK
        prefers a key over the runner token)."""
        from datatorch.core import env as env_names
        from datatorch.runner.directory import runner_directory

        values = {}
        settings = runner_directory.settings
        if settings.api_url and not os.environ.get(env_names.API_URL):
            values[env_names.API_URL] = settings.api_url
        if settings.runner_token and not os.environ.get(env_names.RUNNER_TOKEN):
            values[env_names.RUNNER_TOKEN] = settings.runner_token
        # The step's place in the record (0.8.1), so an action can work
        # for "this project" without a project input. Always set by the
        # runner, never inherited: a value left in the environment by an
        # outer process must not describe another run.
        sections = getattr(getattr(self, "variables", None), "variables", None) or {}
        run = sections.get("run") or {}
        step = sections.get("step") or {}
        for name, value in (
            (env_names.PROJECT_ID, run.get("projectId")),
            (env_names.RUN_ID, run.get("id")),
            (env_names.PIPELINE_ID, run.get("pipelineId")),
            (env_names.STEP_ID, step.get("id")),
        ):
            if value:
                values[name] = str(value)
        return values

    def input_env(self) -> dict:
        """Resolved step inputs as $INPUT_<NAME> env vars for the command."""
        return self.variables.env_inputs()

    def check_for_output(self, string: str) -> bool:
        """Parse output variable from string if valid."""
        # ::varname::value tranlatest to varname = value
        result = string.split("::", 2)
        if len(result) != 3:
            return False
        _, var, value = result
        self.outputs[var] = json.loads(value)
        return True

    async def run_cmd(self, command: str, wait: bool = True, env: dict = None):
        """Runs a command using asyncio.

        `env` (resolved step inputs as $INPUT_<NAME>) is merged over the
        agent's own environment — the injection-safe way to pass input
        values to a shell command (see the injection policy in
        docs/Pipelines.md).
        """
        process = await asyncio.create_subprocess_shell(
            command,
            shell=True,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, **self.runner_env(), **(env or {})},
            # Outputs are reported as single `::var::<json>` stdout lines
            # (see check_for_output), so a line can carry an entire fetched
            # page body — asyncio's 64KB default readline limit kills the
            # stream with LimitOverrunError on anything larger.
            limit=STDOUT_LINE_LIMIT,
            # Its own session and process group, so a stop can signal the
            # step's whole tree at once without touching the runner (see
            # _terminate). Ignored on Windows.
            start_new_session=True,
        )
        if wait:
            await process.wait()
        return process

    def log(self, message: str):
        message = message.strip("\n")
        step = self.action.step
        log = step.log if step else print
        log(message)
