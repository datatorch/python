import subprocess
import logging
import os

from .runner import Runner


logger = logging.getLogger(__name__)


class ShellRunner(Runner):
    def __init__(self, config: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.script = config.get("script")
        if self.script is None:
            raise ValueError("A script was not provided.")

    def execute(self):
        script_command = os.path.join(self.action.dir, self.script.strip("/"))

        logger.info("Running shell script '{}'".format(script_command))
        self.run_cmd("chmod +x {}".format(script_command))
        completed = self.run_cmd(script_command)

        print(completed.stdout.decode("utf-8"))
