import click
from .folder import folder


@click.group(help="Commands for managing uploads.")
def upload():
    pass


upload.add_command(folder)
