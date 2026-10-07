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
        # Render machine-local refs only; ${{ input.* }} is forbidden here
        # (injection policy). Resolved inputs reach the command as
        # $INPUT_<NAME> environment variables instead.
        command = self.get_command("command")
        await self.monitor_cmd(str(command), env=self.input_env())
