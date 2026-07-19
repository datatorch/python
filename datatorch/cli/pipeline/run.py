import click
import asyncio

from datatorch.agent.pipelines import Pipeline, Job
from datatorch.agent import setup_logging


@click.command(help="Runs a pipeline yaml file on local machine.")
@click.argument("path", type=click.Path(exists=True))
def run(path):
    setup_logging()

    async def run_jobs(pipeline: Pipeline):
        """Run jobs in parallel (steps within a job run sequentially)."""
        tasks = []
        for name, config in pipeline.config.get("jobs").items():
            config["name"] = name
            tasks.append(Job(config).run())

        await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.run(run_jobs(Pipeline.from_yaml(path)))
