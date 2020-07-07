import sys
import signal
import logging
import asyncio

from concurrent.futures import ThreadPoolExecutor
from .flows import Flow
from .loop import Loop
from .client import AgentApiClient
from .log_handler import AgentAPIHandler
from .threads import AgentSystemStats
from .directory import AgentDirectory


logger = logging.getLogger(__name__)


class Agent(object):
    @staticmethod
    def install_dependencies(self):
        pass

    def __init__(self, id: str, api: AgentApiClient):
        self.id = id
        self.api = api
        self._loop = True

        self._register_signals()

        self._init_logger()
        self._init_threads()
        self._init_directory()

    def _register_signals(self):
        def signal_handler(sig, frame):
            print("")
            self.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

    def _init_logger(self):
        self.logger = logging.getLogger("datatorch.agent")
        self.logger_api_handler = AgentAPIHandler(self.api)
        self.logger.addHandler(self.logger_api_handler)
        self.logger.debug("Agent logger has been initalized.")

    def _init_threads(self):
        self.threads = AgentThread(self)

    def _init_directory(self):
        self.directory = AgentDirectory()

    def exit(self, code: int = 0):
        """ Safely exits agent. """
        self.logger.info("Attempting to safely exit process.")
        self.logger.debug("Closing threads.")
        self.threads.shutdown()
        self.logger.debug("Closing event loop.")
        self.stop_running()
        self.logger.info("Uploading file logs and exiting process.")
        self.logger_api_handler.upload()
        self.logger.debug("Exiting process.")
        sys.exit(code)

    def run_forever(self):
        """ Runs agent in loop, waiting for jobs. """
        Loop.add_task(self._process_loop())
        Loop.run_forever()

    def stop_running(self):
        """ Exits async loop. """
        Loop.stop()

    async def _process_loop(self):
        """ Waits for jobs from server. """
        logger.info("Waiting for jobs.")
        async for job in self.api.agent_jobs():
            Loop.add_task(self._run_job(job))

    async def _run_job(self, job):
        """ Runs a job """
        logger.info(f"Starting {job.get('createJob').get('id')}")
        flow = Flow.from_yaml("./examples/flow.yaml")
        await flow.run(0)
        logger.info(f"Finishing {job.get('createJob').get('id')}")


class AgentThread(object):
    def __init__(self, agent: Agent, start=True):
        self.agent = agent
        self.system_stats = AgentSystemStats(agent)
        self.pool = ThreadPoolExecutor()

        if start:
            self.start()

    def start(self):
        self.system_stats.start()

    def shutdown(self):
        self.system_stats.shutdown()
        self.pool.shutdown(wait=True)
