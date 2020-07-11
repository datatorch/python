import click

from .start import start
from .create import create
from .dir import dir


@click.group(help="Commands for managing agents.")
def agent():
    pass


agent.add_command(start)
agent.add_command(create)
agent.add_command(dir)
