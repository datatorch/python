import os
from typing import Union
from datatorch.utils.files import mkdir_exists
from datatorch.core import Settings, folder, env, user_settings


class RunnerDirectory(object):
    @staticmethod
    def path() -> str:
        """The runner's working directory (actions cache, runs, logs, settings).

        `DATATORCH_RUNNER_PATH` wins, then the pre-rename `DATATORCH_AGENT_PATH`,
        then `<app dir>/runner`. An install that still has `<app dir>/agent`
        from before the rename is moved to `runner` once, so a runner keeps
        its identity, token and cached actions across the upgrade.
        """
        explicit = os.getenv("DATATORCH_RUNNER_PATH") or os.getenv(
            "DATATORCH_AGENT_PATH"
        )
        if explicit:
            return explicit
        app = folder.get_app_dir()
        new = os.path.join(app, "runner")
        old = os.path.join(app, "agent")
        if not os.path.exists(new) and os.path.isdir(old):
            try:
                os.rename(old, new)
            except OSError:
                return old
        return new

    def __init__(self):
        self.settings = RunnerSettings()

        mkdir_exists(self.dir)
        mkdir_exists(self.db_dir)
        mkdir_exists(self.logs_dir)
        mkdir_exists(self.temp_dir)
        mkdir_exists(self.runs_dir)
        mkdir_exists(self.actions_dir)
        mkdir_exists(self.projects_dir)

    @property
    def root(self):
        return self.path()

    @property
    def dir(self):
        return self.path()

    @property
    def runs_dir(self):
        return os.path.join(self.dir, "runs")

    @property
    def logs_dir(self):
        """Directory where agent logs are stored."""
        return os.path.join(self.dir, "logs")

    @property
    def db_dir(self):
        """Sqlite database are stored."""
        return os.path.join(self.dir, "db")

    @property
    def projects_dir(self):
        """Directory where projects are stored.

        Commonly used for caching project information such as annotations and
        files.
        """
        return os.path.join(self.dir, "projects")

    @property
    def actions_dir(self):
        """Directory where actions are stored."""
        return os.path.join(self.dir, "actions")

    def open(self, file: str, mode: str):
        return open(os.path.join(self.dir, file), mode)

    def action_dir(self, name: str, version: str):
        return os.path.join(self.actions_dir, *name.lower().split("/"), version)

    def run_dir(self, task_id: str):
        """Returns the directory for a given task"""
        path = os.path.join(self.runs_dir, task_id)
        mkdir_exists(path)
        return path

    def project_dir(self, project_id: str):
        """Returns the directory for a given project"""
        path = os.path.join(self.projects_dir, project_id)
        mkdir_exists(path)
        return path

    @property
    def temp_dir(self):
        return os.path.join(self.dir, "temp")


class RunnerSettings(Settings):
    """The runner's own settings file. Keys are `runnerId` / `runnerToken`;
    the pre-rename `agentId` / `agentToken` are still read, so an upgraded
    runner keeps working until it is re-registered."""

    def __init__(self):
        super().__init__(RunnerDirectory.path())

    @property
    def runner_id(self):
        return (
            os.getenv(env.RUNNER_ID)
            or self.get("runnerId", env=env.AGENT_ID)
            or self.get("agentId")
        )

    @runner_id.setter
    def runner_id(self, value):
        self.set("runnerId", value)

    @property
    def runner_token(self):
        return self.get("runnerToken") or self.get("agentToken")

    @runner_token.setter
    def runner_token(self, value):
        self.set("runnerToken", value)

    # Pre-rename names, kept for callers outside this package.
    agent_id = runner_id
    agent_token = runner_token

    @property
    def api_url(self):
        return self.get("apiUrl", user_settings.api_url)

    @api_url.setter
    def api_url(self, value):
        self.set("apiUrl", value)


runner_directory = RunnerDirectory()

# Pre-rename names, kept for callers outside this package.
AgentDirectory = RunnerDirectory
AgentSettings = RunnerSettings
agent_directory = runner_directory
