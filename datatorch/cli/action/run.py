import json
import click
import yaml
import os
import asyncio
import logging

from datatorch.agent import logger
from datatorch.agent.pipelines.action import Action
from datatorch.agent.pipelines.template import Variables, create_variables_mock
from datatorch.agent.pipelines.action.config import ActionConfig
from datatorch.agent.client import AgentJobConfig, AgentRunConfig


def _prompt_for_inputs(action: Action, variables: Variables):
    if len(action.inputs) > 0:
        click.echo(
            click.style("Please fill out the input properties:", fg="blue", bold=True)
        )

    for name, props in action.inputs.items():
        default = props.get("default", None)
        required = props.get("required", False)
        r = click.prompt(f"{name}", default=default, show_default=not required)
        variables.add_input(name, r)


def _create_local_action(folder: str):
    folder_abs = os.path.abspath(folder)
    folder_name = os.path.dirname(folder_abs)
    action_name = f"{folder_name}@local"

    action_config = ActionConfig(action_name)
    return Action(action_config, directory=folder)


def _is_action_directory(folder: str):
    yaml_file = os.path.join(folder, "action-datatorch.yaml")
    return os.path.exists(yaml_file)


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

    if not _is_action_directory(folder):
        return

    action = _create_local_action(folder)

    variables = create_variables_mock()
    variables.set_action(action)

    _prompt_for_inputs(action, variables)

    async def run_action():
        click.echo(click.style("\nAction Logs:", bold=True, fg="blue"))
        output = await action.run(variables)

        click.echo(click.style("\nAction Output:", bold=True, fg="blue"))
        click.echo(
            json.dumps(output, indent=4, sort_keys=True) if output else "No output."
        )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_action())
