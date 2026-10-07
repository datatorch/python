import os
import click
import platform
import subprocess
from datatorch.runner import runner_directory


@click.command(help="Opens the runner directory where settings and files are stored.")
def dir():
    path = runner_directory.dir
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])
