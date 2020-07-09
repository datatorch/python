import sys
import json
import subprocess
import urllib.request
import pkg_resources


def get_latest() -> str:
    contents = urllib.request.urlopen("https://pypi.org/pypi/datatorch/json").read()
    data = json.loads(contents)
    return data["info"]["version"]


def get_version() -> str:
    return pkg_resources.get_distribution("datatorch").version


def upgrade():
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "datatorch", "-U"],
        stdout=subprocess.DEVNULL,
    )
