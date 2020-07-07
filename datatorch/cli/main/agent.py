import os
import click
import logging

from gql.transport.exceptions import TransportServerError

from logging.handlers import RotatingFileHandler
from datatorch.agent import Agent, AgentDirectory
from datatorch.core import env, settings, BASE_URL_API
from datatorch.agent.client import AgentApiClient
from datatorch.utils.package import get_version

from ..spinner import Spinner


def _setup_logging():
    logs_dir = AgentDirectory().logs_dir
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


def _setup_api(host) -> AgentApiClient:
    spinner = Spinner(f"Connecting to DataTorch API ({host})")
    api = AgentApiClient(api_url=host)

    try:
        success = api.validate_endpoint()
    except TransportServerError:
        spinner.done(
            "An error occured while attempting to connect. Are you using the latest version?"
        )
        return

    if not success:
        if host == BASE_URL_API:
            spinner.done(
                "Could not connect. Server is under mantiance, please check back later."
            )
        else:
            spinner.done("Failed to connect. Did you enter the correct endpoint?")
        return

    spinner.done(f"Successfully connected to {host}")
    return api


@click.command(help="Run an agent")
@click.option(
    "--host", default=BASE_URL_API, help="Specify a specific instance of DataTorch"
)
def agent(host):

    _setup_logging()
    api = _setup_api(host)

    click.echo(click.style(f"DataTorch Agent {get_version()}", fg="blue", bold=True))

    agent_id = os.getenv(env.AGENT_ID)
    agent = Agent(agent_id, api)
    agent.run_forever()
