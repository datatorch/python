import asyncio
from asyncio import IncompleteReadError
import logging
from typing import cast
import click
import os

from logging.handlers import RotatingFileHandler


from datatorch.utils.package import get_version

from .directory import agent_directory
from .agent import Agent, tasks

from gql.transport.exceptions import TransportClosed, TransportServerError
from gql.transport.websockets import WebsocketsTransport
from websockets.exceptions import InvalidMessage, InvalidOrigin, InvalidURI
from websockets import ConnectionClosedError

from gql import Client as GqlClient
from datatorch.api import Client as DtClient

__all__ = ["Agent", "start", "stop"]


logger = logging.getLogger(__name__)


_url = agent_directory.settings.api_url
_agent_token = agent_directory.settings.agent_token


BACKOFF_INIT_WAIT = 2
BACKOFF_FACTOR = 1.5
BACKOFF_MAX = 900


def setup_logging() -> None:
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


async def _exit_jobs() -> None:
    """ Exits active running agent jobs """
    logger.info(f"Exiting {len(tasks)} active jobs.")
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


async def _close_transport(transport: WebsocketsTransport):
    """Make sure transport is close.

    If transport is not explicitly closed tasks will hang when cancelled.
    """
    is_closing = transport.close_task is not None
    already_closed = transport.websocket is None

    if not already_closed and not is_closing:
        logger.info("Closing websocket connection.")
        await transport.close()


async def _exit_tasks() -> None:
    """ Exits all active asyncio tasks """
    tasks = [
        task
        for task in asyncio.Task.all_tasks()
        if task is not asyncio.tasks.Task.current_task()  # type: ignore
    ]

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)


async def start() -> None:
    """ Creates and runs an agent. """
    setup_logging()

    click.echo(
        click.style(f"Starting DataTorch Agent v{get_version()}", fg="blue", bold=True)
    )
    logger.debug(f"API Endpoint at {_url}")
    backoff_wait = BACKOFF_INIT_WAIT

    transport = DtClient.create_socket_transport(_url, _agent_token, agent=True)
    client = GqlClient(transport=transport, fetch_schema_from_transport=True)

    while True:
        try:
            async with client as session:
                backoff_wait = BACKOFF_INIT_WAIT
                await Agent.run(session)

        except (
            ConnectionClosedError,
            ConnectionRefusedError,
            IncompleteReadError,
            TransportServerError,
            TransportClosed,
            InvalidMessage,
        ) as e:
            await _exit_jobs()
            await _close_transport(transport)
            await _exit_tasks()

            logger.error(e)
            backoff_wait = min(BACKOFF_MAX, backoff_wait * BACKOFF_FACTOR)
            logger.debug(
                f"Sleeping for {round(backoff_wait)} seconds and then attempting restart."
            )
            await asyncio.sleep(backoff_wait)

        except (asyncio.CancelledError, InvalidURI):
            break

    logger.info("Exiting job processing task.")


async def stop() -> None:
    """ Stop all run tasks. """

    print(" ")

    logger.warning("Gracefully exiting agent.")

    logger.info("Closing agent jobs.")
    await _exit_jobs()

    logger.info("Closing all other tasks.")
    await _exit_tasks()

    loop = asyncio.get_event_loop()
    loop.stop()
