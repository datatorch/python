import click
import yaml
import asyncio
import logging

from datatorch.agent.flows import Flow
from datatorch.agent import logger


class FlowRun(object):
    pass


@click.command(help="Runs a flow yaml file on local machine.")
@click.argument("path", type=click.Path(exists=True))
def run(path):
    logger.setLevel(logging.DEBUG)

    async def run_jobs(flow: Flow):
        """ Run tasks in parallel """
        tasks = []
        for job in flow.jobs:
            tasks.append(job.run())

        await asyncio.wait(tasks)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_jobs(Flow.from_yaml(path)))
