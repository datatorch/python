import click
import yaml
import os
import asyncio
import logging
import json

from datatorch.agent import logger
from datatorch.agent.pipelines.action import Action


input_types = {"string": str, "boolean": bool, "number": float}


@click.command(help="Runs an action locally.")
@click.option(
    "-f",
    "--folder",
    type=click.Path(exists=True, file_okay=False),
    default="./",
    help="Action root directory.",
)
def run(folder):
    logger.setLevel(logging.DEBUG)

    action = Action(directory=folder)

    if len(action.inputs) > 0:
        click.echo(
            click.style("Please fill out the input properties:", fg="blue", bold=True)
        )

    inputs = {}
    for name, props in action.inputs.items():
        default = props.get("default", None)
        required = props.get("required", False)
        input_type = props.get("type", "string")
        r = click.prompt(
            f"{name}",
            default=default,
            show_default=not required,
            type=input_types[input_type],
        )
        inputs[name] = r

    async def run_action():
        click.echo(click.style("\nAction Log:", bold=True))
        output = await action.run(inputs)
        click.echo(click.style("Action Output:", bold=True))
        if output:
            click.echo(yaml.dump(output))
        else:
            click.echo("No output found.")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_action())
