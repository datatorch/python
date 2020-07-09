import logging
import click
import sys
import os

from gql.transport.exceptions import TransportServerError
from logging.handlers import RotatingFileHandler

from datatorch.cli.spinner import Spinner
from datatorch.core import user_settings
from datatorch.utils.package import get_version

from .directory import agent_directory
from .client import AgentApiClient
from .agent import Agent


__all__ = ["Agent", "start"]


def _setup_logging():
    logs_dir = agent_directory.logs_dir
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


def _setup_api() -> AgentApiClient:
    host = user_settings.api_url

    spinner = Spinner(f"Connecting to DataTorch API ({host})")
    api = AgentApiClient()

    try:
        success = api.validate_endpoint()
    except TransportServerError as ex:
        spinner.done(
            click.style(
                "An error occurred while attempting to connect. Are you using the latest version?",
                fg="red",
            )
        )
        click.echo(ex)
        sys.exit()
        return

    spinner.done(f"Successfully connected to {host}.")
    return api


def start():
    _setup_logging()
    api = _setup_api()

    click.echo(
        click.style(f"Starting DataTorch Agent v{get_version()}", fg="blue", bold=True)
    )

    agent = Agent(api)
    agent.run_forever()
