import os
import sys
import click
import logging
import subprocess

from logging.handlers import RotatingFileHandler
from datatorch.agent import Agent, AgentDirectory
from datatorch.core import env, settings, BASE_URL_API
from datatorch.agent.client import AgentApiClient
from datatorch.utils.package import get_latest, get_version, upgrade
from datatorch.utils.files import mkdir_exists
from ..spinner import Spinner

logger = logging.getLogger(__name__)


@click.command(help="Login to DataTorch and stores credentials locally")
@click.argument("key", nargs=-1)
@click.option(
    "--host",
    default=BASE_URL_API,
    help="Url to to a specific API instance of DataTorch",
)
@click.option(
    "--no-web", is_flag=True, help="Disable opening webbrowser to access token link"
)
def login(key, host, no_web):
    key: str = next(iter(key), None)

    if key is None:
        styled_url = click.style(host, fg="blue", bold=True)
        click.echo("Retrieve your API key from: {}".format(styled_url))

        if not no_web:
            import webbrowser

            webbrowser.open(f"{host}/settings/access-tokens")

        key = click.prompt(click.style("Paste your API Key", bold=True)).strip()

    try:
        if len(key) != 36:
            raise ValueError("Key must be 40 characters long.")
        settings.set("API_KEY", key, globally=True)
        settings.set("API_URL", host, globally=True)
    except Exception as ex:
        click.echo(click.style(f"[ERROR] {ex}", fg="red"))


@click.command(help="Upgrade to latests version of python package")
def upgrade():
    spinner = Spinner("Check if newer version is available.")

    latest = get_latest()
    current = get_version()

    if latest == current:
        spinner.done("You are using the most recent version.")
    else:
        spinner.done("New version found: " + click.style(latest, fg="blue", bold=True))
        spinner = Spinner("Upgrading from {} to {}".format(current, latest))
        upgrade()
        spinner.done("Done upgrading from {} to {}".format(current, latest))
    click.echo(
        click.style("Success!", fg="green")
        + " Active version: "
        + click.style(latest, fg="green")
    )


@click.command(help="Run an agent")
@click.option(
    "--host", default=BASE_URL_API, help="Specify a specific instance of DataTorch"
)
def agent(host):

    logs_dir = os.path.join(AgentDirectory.path(), "logs")
    mkdir_exists(logs_dir)
    logging.basicConfig(
        format="%(asctime)s %(name)-30s %(levelname)-8s %(message)s",
        level=logging.WARN,
        handlers=[
            RotatingFileHandler(
                os.path.join(logs_dir, "agent.log"), maxBytes=100000, backupCount=10
            ),
            logging.StreamHandler(),
        ],
    )

    agent_logger = logging.getLogger("datatorch.agent")
    agent_logger.setLevel(logging.DEBUG)

    click.echo(click.style("Connecting to DataTorch API...", fg="blue"))

    api = AgentApiClient(api_url=host)

    if not api.validate_endpoint():
        click.echo(click.style("Could not connect to API!", fg="red"))
        click.echo(click.style("Did you enter the correct endpoint?"))
        return

    click.echo(click.style("Success!", fg="green"))
    agent_id = os.getenv(env.AGENT_ID)

    click.echo(click.style("Starting agent...", fg="blue"))
    agent = Agent(agent_id, api)
    agent.run_forever()
