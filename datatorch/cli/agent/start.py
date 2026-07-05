import click
import asyncio
import signal

from asyncio.events import AbstractEventLoop
from datatorch import agent


def add_signal_handlers(loop: AbstractEventLoop):
    exit_func = lambda: loop.create_task(agent.stop())
    try:
        loop.add_signal_handler(signal.SIGINT, exit_func)
        loop.add_signal_handler(signal.SIGTERM, exit_func)
    except NotImplementedError:
        pass  # Ignore if not implemented. Means this program is running in windows.


@click.command(help="Run an agent")
def start():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(agent.start())
    add_signal_handlers(loop)
    loop.run_forever()
