import os
import sys
import json
import shlex

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
        main_path = os.path.join(self.action.dir, main)

        # Inputs reach the action verbatim as one JSON argv argument.
        # shlex.quote covers every shell metacharacter, apostrophes
        # included, and the space in macOS "Application Support" paths.
        json_input = json.dumps(self.variables.inputs)

        await self.monitor_cmd(
            " ".join(
                shlex.quote(part) for part in (sys.executable, main_path, json_input)
            )
        )
