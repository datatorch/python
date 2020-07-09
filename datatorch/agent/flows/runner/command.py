import logging

from .runner import Runner


logger = logging.getLogger(__name__)


class CommandRunner(Runner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.config.get("command") is None:
            raise ValueError("A command was not provided to run.")

    async def execute(self):
        command = self.get("command")
        completed = await self.run_cmd(command)
        async for log in completed.stdout:
            print(log)
