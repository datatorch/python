import click
import asyncio
import functools

from asyncio.events import AbstractEventLoop
from signal import SIGINT, SIGTERM
from datatorch.agent import start as start_agent
from datatorch.agent import stop as stop_agent


def add_signal_handlers(loop: AbstractEventLoop):    
    exit_func = functools.partial(asyncio.ensure_future, stop_agent())
    try:
        loop.add_signal_handler(SIGINT, exit_func)
        loop.add_signal_handler(SIGTERM, exit_func)
    except NotImplementedError:
        pass  # Ignore if not implemented. Means this program is running in windows.


@click.command(help="Run an agent")
def start():
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(start_agent())
    add_signal_handlers(loop)
    loop.run_forever()
