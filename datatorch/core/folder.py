import os

from click import get_app_dir as get_default_app_directory
from datatorch.core import env
from datatorch.utils.files import mkdir_exists


def get_app_dir():
    """Gets the DataTorch app directory for storing settings.

    If defined, the environment variable `DATATORCH_DIR` will take precedent.
    """
    path = os.getenv(env.CONFIG_DIR) or get_default_app_directory("DataTorch")
    mkdir_exists(path)
    return path
