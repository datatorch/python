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


async def start():

    _setup_logging()

    click.echo(
        click.style(f"Starting DataTorch Agent v{get_version()}", fg="blue", bold=True)
    )

    await Agent.run()

def stop(agent_task):
    print('')
    agent_logger = logging.getLogger("datatorch.agent")
    agent_logger.debug('Gracefully exiting agent.')
    agent_task.cancel()
    agent_logger.debug('Closing websocket')