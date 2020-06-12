import click
import logging
import os

from datatorch.agent import Agent
from datatorch.core import env, settings, BASE_URL


logger = logging.getLogger(__name__)


@click.command()
@click.argument("key", nargs=-1)
@click.option(
    "--host", default=BASE_URL, help="Url to to a specific API instance of DataTorch"
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

        api_url = f"{host}/api"

        settings.set("API_KEY", key, globally=True)
        settings.set("API_URL", api_url, globally=True)
    except Exception as ex:
        click.echo(click.style(f"[ERROR] {ex}", fg="red"))


@click.command()
@click.option(
    "--host", default=BASE_URL, help="Specify a specific instance of DataTorch"
)
def agent(host):
    click.echo(click.style("Starting agent...", fg="green"))

    logging.basicConfig(
        level=logging.DEBUG, format="%(threadName)-10s %(levelname)-8s %(message)s"
    )

    agent_id = os.getenv(env.AGENT_ID)

    Agent(agent_id, host=host)
