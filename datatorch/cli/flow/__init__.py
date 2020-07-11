import click

from .run import run
from .generate import generate
from .upload import upload


@click.group()
def flow():
    pass


flow.add_command(run)
flow.add_command(generate)
flow.add_command(upload)
