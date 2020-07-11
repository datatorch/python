import os
import json
import asyncio

from typing import Awaitable
from ..template import render


class ProcessCodeError(Exception):
    pass


class Runner(object):
    def __init__(self, config, action):
        self.config = config
        self.action = action
        self.original_wd = os.getcwd()

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

    def original_dir(self):
        """ Changes the current work directory back to the original. """
        os.chdir(self.original_wd)

    async def run_cmd(self, command: str, wait=True):
        process = await asyncio.create_subprocess_shell(
            command, shell=True, stdout=asyncio.subprocess.PIPE
        )
        if wait:
            await process.wait()
        return process

    async def monitor_cmd(self, command: str):
        """ Excutes a command and monitors stdout for variables and logging. """
        process = await self.run_cmd(command)

        async for log in process.stdout:
            log = log.decode("utf-8")
            self.check_for_output(log)
            print(log, end="")

        if process.returncode != 0:
            raise ProcessCodeError(
                f"Process failed with exit code {process.returncode}"
            )

    def get(self, key, default=None):
        """ Gets a string from config and renders template. """
        return self.template(self.config.get(key, default), {"variable": self.inputs})

    def template(self, string, variables={}) -> str:
        return render(string, variables or {})

    def check_for_output(self, string: str) -> bool:
        """ Parse output variable from string if valid. """
        result = string.split("::", 2)
        if len(result) != 3:
            return False
        _, var, value = result
        self.outputs[var] = json.loads(value)
        return True
