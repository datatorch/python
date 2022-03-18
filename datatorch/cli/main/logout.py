import click

from datatorch.core import user_settings


@click.command(help="Removes stored user credentials.")
def logout():
    user_settings.api_url = None
    user_settings.api_key = None
    user_settings.set("userLogin", None)
    user_settings.set("userName", None)
    click.echo("Successfully logged out. Goodbye.")
