import os
import docker
import signal
import logging
import asyncio

from typing import Union
from datatorch.utils.files import mkdir_exists

from .client import AgentApiClient
from .log_handler import AgentAPIHandler
from .threads import AgentSystemStats


logger = logging.getLogger(__name__)


class Agent(object):
    def __init__(self, id: str, api: AgentApiClient):
        self.id = id
        self.api = api
        self._loop = True

        self._register_signals()

        self._init_logger()
        self._init_docker()
        self._init_threads()
        self._init_directory()

    def _register_signals(self):
        def signal_handler(sig, frame):
            print("")
            self.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

    def _init_docker(self):
        self.logger.debug("Initalizing docker")
        self.docker = docker.from_env()

    def _init_logger(self):
        self.logger = logging.getLogger("datatorch.agent")
        self.logger_api_handler = AgentAPIHandler(self.api)
        self.logger.addHandler(self.logger_api_handler)
        self.logger.debug("Agent logger has been initalized.")

    def _init_threads(self):
        self.threads = AgentThread(self, start=True)

    def _init_directory(self):
        self.directory = AgentDirectory(self)

    def exit(self, code: int = 0):
        self.logger.debug("Attempting to safely exit process.")
        self.threads.shutdown()
        self.logger.info("Exiting process.")
        self.logger_api_handler.upload()
        exit(code)

    async def process_tasks(self):
        await asyncio.sleep(2)
        await asyncio.sleep(2)
        self.exit()


class AgentThread(object):
    def __init__(self, agent: Agent, start=False):
        self.agent = agent
        self.system_stats = AgentSystemStats(agent)

        if start:
            self.start()

    def start(self):
        self.system_stats.start()

    def shutdown(self):
        self.system_stats.shutdown()


class AgentDirectory(object):
    @staticmethod
    def path():
        home = os.path.expanduser("~")
        return os.path.join(home, "datatorch")

    def __init__(self, agent: Agent):
        self.agent = agent
        self.home = os.path.expanduser("~")

        mkdir_exists(self.dir)
        mkdir_exists(self.tasks_dir)
        mkdir_exists(self.logs_dir)
        mkdir_exists(self.projects_dir)

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

    def open(self, file: str, mode: str):
        return open(os.join(self.directory, file), mode)

    def task_dir(self, task: Union[str, dict]):
        """ Returns the directory for a given task """
        if isinstance(task, str):
            task_id = task
        else:
            task_id = task.get('id')
        return os.path.join(self.tasks_dir, task_id)
    
    def project_dir(self, project: Union[str, dict]):
        """ Returns the directory for a given project """
        if isinstance(project, str):
            project_id = project
        else:
            project_id = project.get('id')
        return os.path.join(self.projects_dir, project_id)
