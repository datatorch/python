import os
import json
import typing
import asyncio

from typing import Any, Awaitable, Dict
from ..template import Variables

if typing.TYPE_CHECKING:
    from ..action import Action


class ProcessCodeError(Exception):
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
        running it receives ``CancelledError`` — the child process is killed
        promptly instead of being orphaned.
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
        """Kill a still-running child process (best effort)."""
        if process.returncode is not None:
            return
        try:
            process.kill()
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
            env={**os.environ, **(env or {})},
        )
        if wait:
            await process.wait()
        return process

    def log(self, message: str):
        message = message.strip("\n")
        step = self.action.step
        log = step.log if step else print
        log(message)
