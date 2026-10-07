import click

from .start import start
from .create import create
from .dir import dir


@click.group(
    name="runner",
    help=(
        "Commands for managing runners — self-hosted compute that "
        "executes pipeline jobs. (Formerly 'agent'.)"
    ),
)
def runner():
    pass


runner.add_command(start)
runner.add_command(create)
runner.add_command(dir)

# Deprecated alias: `datatorch agent <cmd>` keeps working for existing
# installs/scripts, sharing the exact command objects; hidden from
# --help so new users learn `runner`. The wire protocol (agent token,
# GraphQL mutations) and the on-disk agent directory are unchanged.
agent = click.Group(
    name="agent",
    commands=runner.commands,
    hidden=True,
    help="Deprecated alias for 'runner'.",
)
