import click
from datatorch.agent import start as start_agent


@click.command(help="Run an agent")
def start():
    start_agent()
