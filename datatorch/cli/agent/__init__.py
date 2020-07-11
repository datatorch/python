import click

from .start import start
from .create import create


@click.group(help="Commands for managing agents.")
def agent():
    pass


agent.add_command(start)
agent.add_command(create)
