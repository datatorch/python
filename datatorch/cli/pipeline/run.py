import click
import yaml
import asyncio

from datatorch.agent.pipelines import Pipeline, Job
from datatorch.agent import setup_logging


@click.command(help="Runs a pipeline yaml file on local machine.")
@click.argument("path", type=click.Path(exists=True))
def run(path):
    setup_logging()

    async def run_jobs(flow: Pipeline):
        """ Run tasks in parallel """

        tasks = []
        for k, v in flow.config.get("jobs").items():
            v["name"] = k
            tasks.append(Job(v).run())

        await asyncio.wait(tasks)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_jobs(Pipeline.from_yaml(path)))
