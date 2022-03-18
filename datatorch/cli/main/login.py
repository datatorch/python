import click

from datatorch.core import BASE_URL, user_settings
from datatorch.api import ApiClient
from ..spinner import Spinner
from .logout import logout


@click.command(help="Login to DataTorch and store credentials locally.")
@click.argument("key", nargs=-1)
@click.option(
    "--host",
    default=user_settings.api_url or BASE_URL,
    help="Url to to a specific API instance of DataTorch.",
)
@click.option(
    "--no-web",
    is_flag=True,
    help="Disable opening of the web browser to access token link.",
)
@click.option("--relogin", is_flag=True, help="Force relogin if already logged in.")
def login(key, host, no_web, relogin):  # type: ignore
    key: str = next(iter(key), None)  # type: ignore
    host = host.strip("/")

    login = user_settings.get("userLogin")
    if login and not relogin:
        login = click.style(login, fg="blue", bold=True)
        website = user_settings.api_url.strip("/api")
        click.echo(f"You are already logged in as {login} ({website}).")
        click.echo("Use the `--relogin` flag to force relogin.")
        return

    if key is None:
        base_url = host.strip("/api")
        web_url = f"{base_url}/settings/access-tokens"
        styled_url = click.style(web_url, fg="blue", bold=True)
        click.echo("Retrieve your API key from {}".format(styled_url))

        if not no_web:
            import webbrowser

            webbrowser.open(web_url)

        key = click.prompt(click.style("Paste your API key")).strip()

    if len(key) != 36:
        click.echo(click.style("Key must be 36 characters long."))

    user_settings.api_url = host
    user_settings.api_key = key

    spinner = Spinner("Validating API key")
    try:
        api = ApiClient()
        user = api.viewer()
        user_settings.set("userLogin", user.login)
        user_settings.set("userName", user.name)
        spinner.done("Successfully logged in.")

        hello = click.style(user.display_name, fg="blue", bold=True)
        click.echo(f"Hello, {hello}!")
    except Exception as ex:
        spinner.done(
            click.style(
                f"Error connecting to API {user_settings.api_url}!",
                fg="red",
                bold=True,
            )
        )
        logout

        print(ex)
