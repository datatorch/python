import os
import sys
import signal
import logging
import asyncio

from signal import SIGINT, SIGTERM

from concurrent.futures import ThreadPoolExecutor
from .flows import Flow
from .loop import Loop
from .client import AgentApiClient
from .log_handler import AgentAPIHandler
from .threads import AgentSystemStats
from .directory import agent_directory

from gql.transport.websockets import WebsocketsTransport
from gql.client import AsyncClientSession, Client


logger = logging.getLogger(__name__)


class Agent(object):
    @classmethod
    async def run(cls):

        url = agent_directory.settings.api_url.strip("/")
        url = url.replace("http", "ws", 1)
        url = f"{url}/graphql"

        tansport = WebsocketsTransport(url=url, headers={})

        async with Client(
            transport=tansport, fetch_schema_from_transport=True,
        ) as session:
            loop = asyncio.get_event_loop()
            agent = cls(session)
            return await agent.process_loop()

    def __init__(self, session: AsyncClientSession):
        self.api = AgentApiClient(session)
        self.directory = agent_directory

        os.chdir(self.directory.dir)

        # self._register_signals()

        self._init_logger()
        self._init_threads()

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
        self.system_stats = AgentSystemStats(self)
        Loop.add_task(self.system_stats.start())

    def exit(self, code: int = 0):
        """ Safely exits agent. """
        self.logger.info("Attempting to safely exit process.")
        self.logger.debug("Closing event loop.")
        Loop.stop()
        # self.stop_running()
        self.logger.info("Uploading file logs and exiting process.")
        self.logger_api_handler.upload()
        self.logger.debug("Exiting process.")

    async def process_loop(self):
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
