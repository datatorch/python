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
from .directory import AgentDirectory


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
