import click
from .bulk import bulk


@click.group(help="Commands for managing uploads.")
def upload():
    pass


upload.add_command(bulk)
