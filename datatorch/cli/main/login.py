import click

from datatorch.core import settings, BASE_URL_API
from ..spinner import Spinner


@click.command(help="Login to DataTorch and stores credentials locally")
@click.argument("key", nargs=-1)
@click.option(
    "--host",
    default=BASE_URL_API,
    help="Url to to a specific API instance of DataTorch",
)
@click.option(
    "--no-web", is_flag=True, help="Disable opening webbrowser to access token link"
)
def login(key, host, no_web):
    key: str = next(iter(key), None)

    if key is None:
        styled_url = click.style(host, fg="blue", bold=True)
        click.echo("Retrieve your API key from: {}".format(styled_url))

        if not no_web:
            import webbrowser

            webbrowser.open(f"{host}/settings/access-tokens")

        key = click.prompt(click.style("Paste your API Key", bold=True)).strip()

    try:
        if len(key) != 36:
            raise ValueError("Key must be 40 characters long.")
        settings.set("API_KEY", key, globally=True)
        settings.set("API_URL", host, globally=True)
    except Exception as ex:
        click.echo(click.style(f"[ERROR] {ex}", fg="red"))
