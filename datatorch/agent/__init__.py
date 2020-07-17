import asyncio
import logging
import click
import os

from logging.handlers import RotatingFileHandler

from datatorch.utils.package import get_version

from .directory import agent_directory
from .agent import Agent

from gql.transport.websockets import WebsocketsTransport
from websockets import ConnectionClosedError
from gql import Client


__all__ = ["Agent", "start", "stop"]


logger = logging.getLogger(__name__)


_url = (agent_directory.settings.api_url or "").strip("/")
_url = _url.replace("http", "ws", 1)
_url = f"{_url}/graphql"

_transport = WebsocketsTransport(
    url=_url, headers={"datatorch-agent-token": agent_directory.settings.agent_token}
)
_client = Client(transport=_transport, fetch_schema_from_transport=True)


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
    jobs = [
        task for task in asyncio.Task.all_tasks() if task.get_name().startswith("job-")
    ]
    logger.info(f"Exiting {len(jobs)} active jobs.")
    for job in jobs:
        job.cancel()
    await asyncio.gather(*jobs, return_exceptions=True)


async def _exit_tasks() -> None:
    """ Exits all active asyncio tasks """
    # ? If transport is not explicitly closed tasks will hang when cancelled
    if _transport.websocket and _transport.close_task is None:
        logger.info("Closing websocket connection.")
        await _transport.close()

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

    backoff_wait = 2
    backoff_factor = 1.5
    backoff_max = 900
    while True:
        try:
            async with _client as session:
                backoff_wait = 2
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
