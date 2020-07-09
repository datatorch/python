import click
import asyncio
from signal import SIGINT, SIGTERM
from datatorch.agent import start as start_agent
from datatorch.agent import stop as stop_agent
from datatorch.agent.loop import Loop



@click.command(help="Run an agent")
def start():
    loop = asyncio.get_event_loop()
    main_task = asyncio.ensure_future(start_agent())

    loop.add_signal_handler(SIGINT, stop_agent, main_task)
    loop.add_signal_handler(SIGTERM, stop_agent, main_task)

    try:
        loop.run_until_complete(main_task)
    finally:
        loop.stop()