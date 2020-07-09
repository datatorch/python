import click
import asyncio
import functools

from signal import SIGINT, SIGTERM
from datatorch.agent import start as start_agent
from datatorch.agent import stop as stop_agent


@click.command(help="Run an agent")
def start():
    loop = asyncio.get_event_loop()
    main_task = asyncio.ensure_future(start_agent())

    exit_func = functools.partial(asyncio.ensure_future, stop_agent())
    loop.add_signal_handler(SIGINT, exit_func)
    loop.add_signal_handler(SIGTERM, exit_func)
    loop.run_forever()
