import click

from datatorch.core.settings import Settings

__all__ = ["Settings", "LOG_STRING", "BASE_URL"]

LOG_STRING = click.style("DataTorch", fg="red", bold=True)
BASE_URL = "https://datatorch.io"
BASE_URL_API = "https://datatorch.io/api"
