import os
import shlex

from .runner import Runner


class ScriptFailedError(Exception):
    pass


class ShellRunner(Runner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.config.get("script") is None:
            raise ValueError("A script was not provided.")

    async def execute(self):
        # `script` is a path; render machine-local refs only (no
        # ${{ input.* }} — injection policy). Inputs reach the script as
        # $INPUT_<NAME> environment variables.
        script = self.get_command("script").strip("/")
        # `script` may carry arguments after the path ("run.sh --flag");
        # only the path is joined to the action dir and quoted, since the
        # dir can contain a space (macOS "Application Support").
        script_path, _, script_args = script.partition(" ")
        quoted_path = shlex.quote(os.path.join(self.action.dir, script_path))
        await self.run_cmd(f"chmod +x {quoted_path}")
        await self.monitor_cmd(
            f"{quoted_path} {script_args}".rstrip(), env=self.input_env()
        )
