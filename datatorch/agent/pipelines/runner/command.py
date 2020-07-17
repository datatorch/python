import logging

from .runner import Runner


logger = logging.getLogger(__name__)


class CommandFailedError(Exception):
    pass


class CommandRunner(Runner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.config.get("command") is None:
            raise ValueError("A command was not provided to run.")

    async def execute(self):
        command = self.config.get("command")
        await self.monitor_cmd(str(command))
