import click
import platform

from datatorch.agent.directory import agent_directory
from datatorch.api import ApiClient
from datatorch.utils.package import get_version
from datatorch.core import user_settings, BASE_URL_API
from ..main.login import login
from ..spinner import Spinner


def create_agent(name: str) -> dict:
    api = ApiClient()
    # fmt: off
    results = api.execute(
        """
        mutation CreateAgent($name: String!, $version: String!) {
            createAgent(name: $name, version: $version) {
                agent {
                    id
                }
                token
            }
        }
        """,
        params=dict(name=name, version=get_version())
    )
    # fmt: on
    return results


@click.command()
@click.pass_context
def create(ctx):
    agent_settings = agent_directory.settings

    if agent_settings.agent_id:
        click.echo("A runner is already installed.")
        confirmed = click.confirm(
            "Would you like to create a new runner?", default=True
        )
        if not confirmed:
            return

    if not user_settings.api_url:
        user_settings.api_url = click.prompt(
            "Enter API endpoint", default=BASE_URL_API, show_default=True
        )

    if not user_settings.api_key:
        ctx.invoke(login, host=user_settings.api_url)

    name = click.prompt("Enter runner name", default=platform.node(), show_default=True)
    spinner = Spinner("Creating runner")

    try:
        agent = create_agent(name)["createAgent"]
        agent_settings.agent_id = agent["agent"]["id"]
        agent_settings.agent_token = agent["token"]
        agent_settings.api_url = user_settings.api_url
    except Exception as ex:
        spinner.done(click.style("Failed to create runner.", fg="red"))
        click.echo(ex)
        return

    spinner.done("Successfully created runner.")
