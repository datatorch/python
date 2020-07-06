import subprocess
import logging

from .runner import Runner


logger = logging.getLogger(__name__)


class CommandRunner(Runner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.config.get("command") is None:
            raise ValueError("A command was not provided to run.")

    def execute(self):
        command = self.get("command")
        completed = self.run_cmd(command)
        print(completed.stdout.decode("utf-8"))
