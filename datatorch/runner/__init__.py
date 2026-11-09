import asyncio
import logging
import click
import os

from logging.handlers import RotatingFileHandler
from asyncio import IncompleteReadError
from typing import List, Optional

from .directory import runner_directory
from .daemon import RunnerDaemon, tasks  # noqa: F401  (tasks: re-exported)

from gql import Client as GqlClient
from gql.transport.exceptions import TransportError, TransportQueryError
from gql.transport.websockets import WebsocketsTransport
from websockets.exceptions import ConnectionClosed, InvalidMessage, InvalidURI

from datatorch.api import Client as DtClient
from datatorch.utils.package import get_version

__all__ = ["RunnerDaemon", "Agent", "start", "stop"]

# Pre-rename name, kept for callers outside this package.
Agent = RunnerDaemon


logger = logging.getLogger(__name__)


_url = runner_directory.settings.api_url
_agent_token = runner_directory.settings.runner_token

# The one daemon of this process; it outlives every websocket connection.
_daemon: Optional[RunnerDaemon] = None


BACKOFF_INIT_WAIT = 2
BACKOFF_FACTOR = 1.5
BACKOFF_MAX = 900


def directories():
    return runner_directory


def setup_logging() -> None:
    logs_dir = runner_directory.logs_dir
    logging.basicConfig(
        format="%(asctime)s %(name)-30s %(levelname)-8s %(message)s",
        level=logging.WARN,
        handlers=[
            RotatingFileHandler(
                os.path.join(logs_dir, "runner.log"), maxBytes=100000, backupCount=10
            ),
            logging.StreamHandler(),
        ],
    )
    logger.setLevel(logging.DEBUG)


def running_steps() -> List[asyncio.Task]:
    """The step tasks this process is running right now."""
    return _daemon.running_steps() if _daemon else []


async def _exit_jobs() -> None:
    """Cancels the running steps. A real shutdown only (`stop`): a lost
    connection does not come through here any more (0.8.3)."""
    steps = running_steps()
    logger.info(f"Exiting {len(steps)} active step(s).")

    for task in steps:
        task.cancel()

    await asyncio.gather(*steps, return_exceptions=True)


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
    """Exits all active asyncio tasks"""
    try:
        current_task = asyncio.current_task()
        all_tasks = asyncio.all_tasks()
    except AttributeError as e:
        current_task = asyncio.Task.current_task()
        all_tasks = asyncio.Task.all_tasks()

    not_current_tasks = [task for task in all_tasks if task is not current_task]

    for task in not_current_tasks:
        task.cancel()


async def _restart_after_failure(transport, backoff_wait: float) -> float:
    """The connection failed: stops this connection's services, closes the
    transport and sleeps with backoff before the caller reconnects.

    Running steps are left running. Before 0.8.3 every step was cancelled
    here, so a four-second websocket blip (a rolling API deploy, a keepalive
    ping timeout) killed hours of work; on 2026-11-09 three such drops
    aborted the org-root dataset-scout seed step 46 seconds in. A step
    that finishes while disconnected holds its result until the daemon is
    connected again (see `RunnerDaemon._report`).

    Returns the next backoff wait."""
    if _daemon is not None:
        _daemon.disconnect()
    await _close_transport(transport)

    steps = running_steps()
    if steps:
        logger.info(f"{len(steps)} step(s) keep running while the connection is down.")

    backoff_wait = min(BACKOFF_MAX, backoff_wait * BACKOFF_FACTOR)
    logger.debug(
        f"Sleeping for {round(backoff_wait)} seconds and then attempting restart."
    )
    await asyncio.sleep(backoff_wait)
    return backoff_wait


async def start() -> None:
    """Creates and runs an agent."""
    setup_logging()

    click.echo(
        click.style(f"Starting DataTorch Runner v{get_version()}", fg="blue", bold=True)
    )
    logger.debug(f"API Endpoint at {_url}")

    transport = DtClient.create_socket_transport(_url, _agent_token, agent=True)
    client = GqlClient(transport=transport, fetch_schema_from_transport=True)
    await serve_forever(client, transport)


async def serve_forever(client, transport, daemon: Optional[RunnerDaemon] = None):
    """Connects, serves, and reconnects with backoff until cancelled.

    `client` is an async gql client (`async with client as session`),
    `transport` its websocket transport. One `RunnerDaemon` is used for
    every connection, so its running steps survive a reconnect."""
    global _daemon
    _daemon = daemon or RunnerDaemon()
    backoff_wait = BACKOFF_INIT_WAIT

    while True:
        try:
            async with client as session:
                backoff_wait = BACKOFF_INIT_WAIT
                await _daemon.serve(session)

        except (asyncio.CancelledError, InvalidURI):
            break

        except (
            # ConnectionClosed covers both the error and the "OK" close
            # (a server-side restart closes cleanly); OSError covers the
            # socket-level failures seen right after a laptop wakes
            # (DNS gaierror, ConnectionReset, ConnectionRefused, timeouts).
            # TransportQueryError is what gql raises when the socket drops
            # while a query is in flight ("Query completed without any
            # answer received from the server"); it is NOT a TransportError
            # subclass in the installed gql, so it is listed on its own.
            ConnectionClosed,
            OSError,
            IncompleteReadError,
            TransportError,
            TransportQueryError,
            InvalidMessage,
            asyncio.TimeoutError,
        ) as e:
            logger.error(e)

        except Exception:
            # Last resort: the loop must never die. On 2026-09-12 an
            # uncaught exception here left the process alive for weeks
            # with no agent loop, so the runner showed OFFLINE while its
            # window looked fine.
            logger.exception("Unexpected error in the agent loop; restarting.")

        try:
            backoff_wait = await _restart_after_failure(transport, backoff_wait)
        except asyncio.CancelledError:
            # A shutdown that lands during the backoff sleep.
            break

    logger.info("Exiting job processing task.")


async def stop() -> None:
    """Stop all run tasks (SIGINT/SIGTERM): running steps are cancelled,
    then every other task, then the loop."""

    print(" ")

    logger.warning("Gracefully exiting runner.")

    logger.info("Closing runner jobs.")
    await _exit_jobs()

    if _daemon is not None:
        _daemon.disconnect()

    logger.info("Closing all other tasks.")
    await _exit_tasks()

    loop = asyncio.get_running_loop()
    loop.stop()
