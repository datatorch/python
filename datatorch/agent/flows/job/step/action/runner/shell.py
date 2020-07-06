import subprocess
import logging
import os

from .runner import Runner


logger = logging.getLogger(__name__)


class ShellRunner(Runner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.config.get("script") is None:
            raise ValueError("A script was not provided.")

    def execute(self):
        script = self.get('script').strip('/')
        script_command = os.path.join(self.action.dir, script)

        self.run_cmd("chmod +x {}".format(script_command))
        completed = self.run_cmd(script_command)

        print(completed.stdout.decode("utf-8"))
