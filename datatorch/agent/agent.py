import os
import logging
import asyncio

from typing import List
from .flows import Flow
from .client import AgentApiClient
from .log_handler import AgentAPIHandler
from .monitoring import AgentSystemStats
from .directory import agent_directory

from gql.client import AsyncClientSession


logger = logging.getLogger(__name__)


class Agent(object):
    @classmethod
    async def run(cls, session):
        agent = cls(session)
        await agent.process_loop()

    def __init__(self, session: AsyncClientSession):
        self.api = AgentApiClient(session)
        self.directory = agent_directory
        self.tasks: List[asyncio.Task] = []

        os.chdir(self.directory.dir)

        self._init_logger()
        self._init_threads()

    def _init_logger(self):
        self.logger = logging.getLogger("datatorch.agent")
        self.logger_api_handler = AgentAPIHandler(self.api)
        self.logger.addHandler(self.logger_api_handler)
        self.logger.debug("Agent logger has been initalized.")

    def _init_threads(self):
        self.system_stats = AgentSystemStats(self)
        loop = asyncio.get_event_loop()
        task = loop.create_task(self.system_stats.start())
        task.set_name("agent-monitoring")

    async def process_loop(self):
        """ Waits for jobs from server. """

        logger.info("Waiting for jobs.")
        async for job in self.api.agent_jobs():
            loop = asyncio.get_event_loop()
            job = job.get("createJob")
            task = loop.create_task(self._run_job(job))
            task.set_name(f"job-{job.get('id')}")

    async def _run_job(self, job):
        """ Runs a job """
        job_id = job.get("id")
        try:
            logger.info(f"Starting {job_id}")
            await asyncio.sleep(120)
            # flow = Flow.from_yaml("./examples/flow.yaml")
            # await flow.run(0)
            logger.info(f"Finishing {job_id}")
        except asyncio.CancelledError:
            logger.info(f"Canceling job {job_id}")
