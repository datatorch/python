import click

from datatorch.utils.package import get_version

# from .main.agent import agent
from .main.login import login
from .main.logout import logout
from .main.upgrade import package_upgrade
from .main.version import version

from .agent import agent
from .flow import flow
from .action import action


@click.group()
@click.version_option(prog_name="DataTorch", version=get_version())
def main():
    pass


main.add_command(login)
main.add_command(logout)
main.add_command(version)
main.add_command(package_upgrade)

main.add_command(flow)
main.add_command(agent)
main.add_command(action)
