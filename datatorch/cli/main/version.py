import click

from datatorch.utils.package import get_version


@click.command(help="Prints current python client version.")
def version():
    click.echo(f"Version: {get_version()}")
