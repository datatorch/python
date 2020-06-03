import click

from datatorch.core.settings import Settings

LOG_STRING = click.style('DataTorch', fg='red', bold=True)
BASE_URL = 'https://datatorch.io'

settings = Settings()
