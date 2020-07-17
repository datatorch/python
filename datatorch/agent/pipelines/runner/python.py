import os
import sys
import json
import base64

from .runner import Runner


class PythonFailedError(Exception):
    pass


class PythonRunner(Runner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.config.get("main") is None:
            raise ValueError("A main path was not provided.")

    async def execute(self):
        main = self.get("main").strip("/")
        main_command = os.path.join(self.action.dir, main)
        json_input = json.dumps(self.variables.inputs).replace("'", '\\"')

        await self.monitor_cmd(f"{sys.executable} {main_command} '{json_input}'")
