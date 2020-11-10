import os
import json
import logging
import asyncio

from typing import List
from .client import AgentApiClient
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

    async def _run_job(self, job):
        """ Runs a job """
        job_id = job.get("id")
        job_name = job.get("name")
        job_steps = job.get("steps")

        run = job.get("run")
        run_config = run.get("config")

        job_config = run_config.get("jobs").get(job_name)
        job_config["id"] = job_id
        job_config["name"] = job_name

        # Match db steps id to flow config steps
        for step in job_config.get("steps"):
            for i, d in enumerate(job_steps):
                if isinstance(step.get("action"), dict):
                    try:
                        same_action = json.loads(d["action"]) == step.get("action")
                    except:
                        same_action = False
                else:
                    same_action = d["action"] == step.get("action")

                same_name = d["name"] == step.get("name")

                if same_action and same_name:
                    step["id"] = job_steps.pop(i).get("id")

            if step.get("id") == None:
                raise ValueError(f"No ID found for step {step.get('action')}.")

        variables = Variables(run)

        try:
            logger.info(f"Starting {job_name} {job_id}")
            await Job(job_config, agent=self).run(variables)
            logger.info(f"Finishing {job_id}")

        except asyncio.CancelledError:
            logger.info(f"Canceling job {job_id}")
