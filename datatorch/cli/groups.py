import click

from .main import commands as main_commands


@click.group()
def main():
    pass


main.add_command(main_commands.login)
main.add_command(main_commands.agent)
main.add_command(main_commands.upgrade)
