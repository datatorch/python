import click

from .create import create
from .pull import pull
from .run import run


@click.group(help="Commands for managing actions.")
def action():
    pass


action.add_command(create)
action.add_command(pull)
action.add_command(run)
