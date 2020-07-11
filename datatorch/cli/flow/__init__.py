import click

from .run import run
from .generate import generate


@click.group()
def flow():
    pass


flow.add_command(run)
flow.add_command(generate)
