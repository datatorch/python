import os
from typing import Union
from datatorch.utils.files import mkdir_exists


class AgentDirectory(object):
    @staticmethod
    def path() -> str:
        home = os.path.expanduser("~")
        default_path = os.path.join(home, "datatorch")
        return os.getenv("AGENT_PATH", default_path)

    def __init__(self):
        self.home = os.path.expanduser("~")

        mkdir_exists(self.dir)
        mkdir_exists(self.tasks_dir)
        mkdir_exists(self.logs_dir)
        mkdir_exists(self.projects_dir)
        mkdir_exists(self.actions_dir)

    @property
    def dir(self):
        return self.path()

    @property
    def tasks_dir(self):
        return os.path.join(self.dir, "tasks")

    @property
    def logs_dir(self):
        """ Directory where agent logs are stored. """
        return os.path.join(self.dir, "logs")

    @property
    def projects_dir(self):
        """ Directory where projects are stored.

        Commonly used for caching project information such as annotations and
        files.
        """
        return os.path.join(self.dir, "projects")

    @property
    def actions_dir(self):
        """ Directory where actions are stored. """
        return os.path.join(self.dir, "actions")

    def open(self, file: str, mode: str):
        return open(os.join(self.directory, file), mode)

    def action_dir(self, name: str, version: str):
        return os.path.join(self.actions_dir, *name.lower().split("/"), version)

    def task_dir(self, task: Union[str, dict]):
        """ Returns the directory for a given task """
        if isinstance(task, str):
            task_id = task
        else:
            task_id = task.get("id")
        return os.path.join(self.tasks_dir, task_id)

    def project_dir(self, project: Union[str, dict]):
        """ Returns the directory for a given project """
        if isinstance(project, str):
            project_id = project
        else:
            project_id = project.get("id")
        return os.path.join(self.projects_dir, project_id)
