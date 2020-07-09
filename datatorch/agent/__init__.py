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
from websockets import ConnectionClosedError
import asyncio
from gql.transport.websockets import WebsocketsTransport
from gql import Client


__all__ = ["Agent", "start"]


logger = logging.getLogger(__name__)


_url = agent_directory.settings.api_url.strip("/")
_url = _url.replace("http", "ws", 1)
_url = f"{_url}/graphql"

_transport = WebsocketsTransport(
    url=_url, headers={"datatorch-agent-token": agent_directory.settings.agent_token}
)
_client = Client(transport=_transport, fetch_schema_from_transport=True)


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

    logger.setLevel(logging.DEBUG)


async def _exit_jobs():
    """ Exits active running agent jobs """

    # ? If transport is not explicitly closed tasks will hang when cancelled
    if _transport.websocket and _transport.close_task is None:
        logger.info("Closing websocket connection.")
        await _transport.close()

    jobs = [
        task for task in asyncio.Task.all_tasks() if task.get_name().startswith("job-")
    ]
    logger.info(f"Exiting {len(jobs)} active jobs.")
    for job in jobs:
        job.cancel()
    await asyncio.gather(*jobs, return_exceptions=True)


async def _exit_tasks():
    """ Exits all active asyncio tasks """
    tasks = [
        task
        for task in asyncio.Task.all_tasks()
        if task is not asyncio.tasks.Task.current_task()
    ]

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)


async def start():
    """ Creates and runs an agent. """

    _setup_logging()

    click.echo(
        click.style(f"Starting DataTorch Agent v{get_version()}", fg="blue", bold=True)
    )

    backoff_wait = 2
    backoff_factor = 1.5
    backoff_max = 900
    while True:
        try:
            async with _client as session:
                await Agent.run(session)

        except (
            ConnectionClosedError,
            ConnectionRefusedError,
            asyncio.IncompleteReadError,
        ) as e:
            await _exit_jobs()
            await _exit_tasks()

            logger.error(e)
            backoff_wait = min(backoff_max, backoff_wait * backoff_factor)
            logger.debug(
                f"Sleeping for {round(backoff_wait)} seconds and then attempting restart."
            )
            await asyncio.sleep(backoff_wait)

        except asyncio.CancelledError:
            logger.info("Exiting job processing task.")
            return


async def stop():
    """ Stop all run tasks. """

    print(" ")

    logger.warning("Gracefully exiting agent.")

    logger.info("Closing agent jobs.")
    await _exit_jobs()

    logger.info("Closing all other tasks.")
    await _exit_tasks()

    loop = asyncio.get_event_loop()
    loop.stop()
