import os
import json
import typing
import asyncio

from datetime import datetime, timezone

from typing import Awaitable
from ..template import render

if typing.TYPE_CHECKING:
    from ..action import Action


class ProcessCodeError(Exception):
    pass


class Runner(object):
    def __init__(self, config: dict, action: "Action"):
        self.config = config
        self.action = action

    async def run(self, inputs: dict = {}):
        self.inputs = inputs
        self.outputs = {}
        await self.execute()
        return self.outputs

    async def execute(self) -> Awaitable[dict]:
        raise NotImplementedError("This method must be implemented.")

    def action_dir(self):
        """ Changes the current work directory to the actions directory. """
        os.chdir(self.action.dir)

    async def monitor_cmd(self, command: str):
        """ Excutes a command and monitors stdout for variables and logging. """
        process = await self.run_cmd(command)

        async for log in process.stdout:
            log = log.decode("utf-8")
            self.check_for_output(log)
            print(log, end="")
            self.log(log)

        if process.returncode != 0:
            raise ProcessCodeError(
                f"Process failed with exit code {process.returncode}"
            )

    def get(self, key: str, default=None):
        """ Gets a string from config and renders template. """
        return self.template(self.config.get(key, default), {"variable": self.inputs})

    def template(self, string: str, variables={}) -> str:
        return render(string, variables or {})

    def check_for_output(self, string: str) -> bool:
        """ Parse output variable from string if valid. """
        result = string.split("::", 2)
        if len(result) != 3:
            return False
        _, var, value = result
        self.outputs[var] = json.loads(value)
        return True

    async def run_cmd(self, command: str, wait: bool = True):
        """ Runs a command using asyncio """
        process = await asyncio.create_subprocess_shell(
            command, shell=True, stdout=asyncio.subprocess.PIPE  # type: ignore
        )
        if wait:
            await process.wait()
        return process

    def log(self, message: str):
        self.action.step.log(message)
