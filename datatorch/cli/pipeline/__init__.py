import click

from .run import run
from .generate import generate
from .upload import upload


@click.group()
def pipeline():
    pass


pipeline.add_command(run)  # type: ignore
pipeline.add_command(generate)  # type: ignore
pipeline.add_command(upload)  # type: ignore
