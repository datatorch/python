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


_url = agent_directory.settings.api_url.strip("/")
_url = _url.replace("http", "ws", 1)
_url = f"{_url}/graphql"

_transport = WebsocketsTransport(url=_url, headers={})
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

    agent_logger = logging.getLogger("datatorch.agent")
    agent_logger.setLevel(logging.DEBUG)


async def start():
    
    _setup_logging()

    click.echo(
        click.style(f"Starting DataTorch Agent v{get_version()}", fg="blue", bold=True)
    )

    agent_logger = logging.getLogger("datatorch.agent")
    while True:
        try:

            async with _client as session:
                await Agent.run(session)

        except (ConnectionClosedError, ConnectionRefusedError) as e:
            # ? When an expection is throw session is not closing transport
            await _transport.close()

            agent_logger.error(e)
            agent_logger.debug("Sleeping for 10 seconds and then attempting restart.")
            await asyncio.sleep(10)
        
        except asyncio.CancelledError:
            agent_logger.warning('Exiting job processing task.')
            return


async def stop():
    print(" ")
    agent_logger = logging.getLogger("datatorch.agent")
    agent_logger.warning("Gracefully exiting agent.")    
    agent_logger.info('Closing agent jobs.')

    # Exit running jobs
    jobs = [
        task
        for task in asyncio.Task.all_tasks()
        if task.get_name().startswith('job-')
    ]
    agent_logger.info(f"Exiting {len(jobs)} active jobs.")
    for job in jobs:
        job.cancel()
    await asyncio.gather(*jobs, return_exceptions=True)

    # Exit all other running tasks
    # ? If transport is not explicitly closed tasks will hang when cancelled
    agent_logger.info('Closing websocket connection.')
    await _transport.close()

    tasks = [
        task
        for task in asyncio.Task.all_tasks()
        if task is not asyncio.tasks.Task.current_task()
    ]

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)

    loop = asyncio.get_event_loop()
    loop.stop()
