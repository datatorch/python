import subprocess
import logging

from .runner import Runner


logger = logging.getLogger(__name__)


class CommandRunner(Runner):
    def __init__(self, config: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.command = config.get("command")
        if self.command is None:
            raise ValueError("A command was not provided to run.")

    def execute(self):
        logger.info("Running command '{}'".format(self.command))
        completed = self.run_cmd(self.command)
        print(completed.stdout.decode("utf-8"))
