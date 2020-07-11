import click
import logging

from datatorch.utils.package import get_latest, get_version, upgrade
from ..spinner import Spinner


logger = logging.getLogger(__name__)


@click.command("upgrade", help="Upgrade to latests version of python package.")
def package_upgrade():
    spinner = Spinner("Check if newer version is available.")

    latest = get_latest()
    current = get_version()

    if latest == current:
        spinner.done("You are using the most recent version.")
    else:
        spinner.done("New version found: " + click.style(latest, fg="blue", bold=True))
        spinner = Spinner("Upgrading from {} to {}".format(current, latest))
        upgrade()
        spinner.done("Done upgrading from {} to {}".format(current, latest))
    click.echo(
        click.style("Success!", fg="green")
        + " Active version: "
        + click.style(latest, fg="green")
    )
