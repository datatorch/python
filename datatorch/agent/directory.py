import os
from typing import Union
from datatorch.utils.files import mkdir_exists
from datatorch.core import Settings, folder, env, user_settings


class AgentDirectory(object):
    @staticmethod
    def path() -> str:
        """ Returns the agents directory """
        path = folder.get_app_dir()
        return os.getenv("DATATORCH_AGENT_PATH", os.path.join(path, "agent"))

    def __init__(self):
        self.settings = AgentSettings()

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
        """ Directory where agent logs are stored. """
        return os.path.join(self.dir, "logs")

    @property
    def db_dir(self):
        """ Sqlite database are stored. """
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
        """ Directory where actions are stored. """
        return os.path.join(self.dir, "actions")

    def open(self, file: str, mode: str):
        return open(os.path.join(self.dir, file), mode)

    def action_dir(self, name: str, version: str):
        return os.path.join(self.actions_dir, *name.lower().split("/"), version)

    def run_dir(self, task_id: str):
        """ Returns the directory for a given task """
        path = os.path.join(self.runs_dir, task_id)
        mkdir_exists(path)
        return path

    def project_dir(self, project_id: str):
        """ Returns the directory for a given project """
        path = os.path.join(self.projects_dir, project_id)
        mkdir_exists(path)
        return path

    @property
    def temp_dir(self):
        return os.path.join(self.dir, "temp")


class AgentSettings(Settings):
    def __init__(self):
        super().__init__(AgentDirectory.path())

    @property
    def agent_id(self):
        return self.get("agentId", env=env.AGENT_ID)

    @agent_id.setter
    def agent_id(self, value):
        self.set("agentId", value)

    @property
    def agent_token(self):
        return self.get("agentToken")

    @agent_token.setter
    def agent_token(self, value):
        self.set("agentToken", value)

    @property
    def api_url(self):
        return self.get("apiUrl", user_settings.api_url)

    @api_url.setter
    def api_url(self, value):
        self.set("apiUrl", value)


agent_directory = AgentDirectory()
