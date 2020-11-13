import click
import asyncio
import functools
import signal

from asyncio.events import AbstractEventLoop
from datatorch import agent


def add_signal_handlers(loop: AbstractEventLoop):
    exit_func = functools.partial(asyncio.ensure_future, agent.stop())
    try:
        loop.add_signal_handler(signal.SIGINT, exit_func)
        loop.add_signal_handler(signal.SIGTERM, exit_func)
    except NotImplementedError:
        pass  # Ignore if not implemented. Means this program is running in windows.


@click.command(help="Run an agent")
def start():
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(agent.start())
    add_signal_handlers(loop)
    loop.run_forever()
