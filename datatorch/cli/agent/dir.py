import os
import click
import platform
import subprocess
from datatorch.agent import agent_directory


@click.command(help="Opens agent directory where settings and files are stored.")
def dir():
    path = agent_directory.dir
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])
