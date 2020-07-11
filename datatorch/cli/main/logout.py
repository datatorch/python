import click

from datatorch.core import user_settings


@click.command(help="Removes stored user credentials.")
def logout():
    user_settings.api_key = ""
    click.echo("Successfully logged out. Goodbye.")
