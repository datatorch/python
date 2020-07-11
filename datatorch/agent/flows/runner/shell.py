import os

from .runner import Runner


class ScriptFailedError(Exception):
    pass


class ShellRunner(Runner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.config.get("script") is None:
            raise ValueError("A script was not provided.")

    async def execute(self):
        script = self.get("script").strip("/")
        script_command = os.path.join(self.action.dir, script)
        await self.run_cmd("chmod +x {}".format(script_command.split(" ", 1)[0]))
        await self.monitor_cmd(script_command)
