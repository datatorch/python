import os
import json
import logging
import asyncio

from typing import List
from .client import AgentApiClient, AgentJobConfig, AgentRunConfig
from .pipelines.template import Variables
from .log_handler import AgentAPIHandler
from .monitoring import AgentSystemStats
from .directory import agent_directory

from gql.client import AsyncClientSession
from datatorch.agent.pipelines import Job


logger = logging.getLogger(__name__)
tasks: List[asyncio.Task] = []


class Agent(object):
    @classmethod
    async def run(cls, session):
        agent = cls(session)
        await agent.process_loop()

    def __init__(self, session: AsyncClientSession):
        self.api = AgentApiClient(session)
        self.directory = agent_directory
        logger.debug(f"Switch to agent directory: {self.directory.dir}")
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
        tasks.append(task)

    async def process_loop(self):
        """ Waits for jobs from server. """
        logger.info("Waiting for jobs.")
        async for job_request in self.api.agent_jobs():
            loop = asyncio.get_event_loop()
            job = job_request.get("job")
            task = loop.create_task(self._run_job(job))
            tasks.append(task)

    async def _run_job(self, job: AgentJobConfig):
        """ Runs a job """
        job_id = job.get("id")
        job_name = job.get("name")
        job_steps = job.get("steps")

        run = job.get("run")
        config = run.get("config")
        config_job = config.get("jobs").get(job_name)

        # Add entity ids to config
        config_job["id"] = job_id
        # Add ids of steps in db to config yaml
        for idx, step in enumerate(config_job.get("steps")):
            step["id"] = job_steps[idx].get("id")

        variables = Variables(job)

        try:
            logger.info(f"Job received (name: {job_name}, id: {job_id})")
            await Job(config_job, agent=self).run(variables)
            logger.info(f"Job finished (name: {job_name}, id: {job_id})")

        except asyncio.CancelledError:
            logger.info(f"Canceling job {job_id}")
