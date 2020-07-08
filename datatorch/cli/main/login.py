import click

from datatorch.core import user_settings, BASE_URL_API
from datatorch.api import ApiClient
from ..spinner import Spinner


@click.command(help="Login to DataTorch and stores credentials locally")
@click.argument("key", nargs=-1)
@click.option(
    "--host",
    default=BASE_URL_API,
    help="Url to to a specific API instance of DataTorch",
)
@click.option(
    "--web", is_flag=True, help="Opens webbrowser to access token link"
)
def login(key, host, web):
    key: str = next(iter(key), None)

    if key is None:
        styled_url = click.style(host, fg="blue", bold=True)
        click.echo("Retrieve your API key from: {}".format(styled_url))

        if web:
            import webbrowser

            webclient_url = host.strip("/").strip("api").strip("/")
            webbrowser.open(f"{webclient_url}/settings/access-tokens")

        key = click.prompt(click.style("Paste your API Key", bold=True)).strip()

    try:
        if len(key) != 36:
            raise ValueError("Key must be 36 characters long.")
        user_settings.api_url = host
        user_settings.api_key = key
    except Exception as ex:
        click.echo(click.style(f"[ERROR] {ex}", fg="red"))
        return
    
    spinner = Spinner('Validating API key')
    api = ApiClient()
    user = api.viewer()
    user_settings.set('userLogin', user.login)
    user_settings.set('userName', user.name)
    spinner.done('Successfully logged in.')
    hello = click.style(user.name or user.login, fg="blue", bold=True)
    click.echo(f'Hello, {hello}!')
