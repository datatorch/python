import sys
import json
import subprocess
import urllib.request
from importlib.metadata import version


def get_latest() -> str:
    contents = urllib.request.urlopen("https://pypi.org/pypi/datatorch/json").read()
    data = json.loads(contents)
    return data["info"]["version"]


def get_version() -> str:
    return version("datatorch")


def upgrade():
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "datatorch", "-U"],
        stdout=subprocess.DEVNULL,
    )
