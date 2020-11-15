from datatorch.agent.pipelines.template import create_variables_mock
import click
import asyncio

from datatorch.agent.pipelines import Pipeline, Job, Variables
from datatorch.agent import setup_logging


@click.command(help="Runs a pipeline yaml file on local machine.")
@click.argument("path", type=click.Path(exists=True))
def run(path):
    setup_logging()

    async def run_jobs(pipeline: Pipeline):
        """ Run tasks in parallel """
        tasks = []
        for k, v in pipeline.config.get("jobs").items():
            config = {
                run: {
                    "config": pipeline.config,
                },
                "steps": v.get("steps"),
            }
            variables = create_variables_mock(config)
            v["name"] = k
            tasks.append(Job(v).run(variables))

        await asyncio.wait(tasks)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_jobs(Pipeline.from_yaml(path)))
