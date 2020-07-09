import click

from datatorch.core import user_settings, BASE_URL_API
from datatorch.api import ApiClient
from ..spinner import Spinner


@click.command(help="Removes stored user credentials")
def logout():
    user_settings.api_key = ""
    click.echo("Successfully logged out. Goodbye.")
