import os
import errno

from datatorch.utils.files import mkdir_exists
from datatorch.core import env


def global_path(mkdir=True):
    user_dir = os.path.join(os.path.expanduser("~"), ".datatorch")
    config_dir = os.getenv(env.CONFIG_DIR) or user_dir
    if mkdir:
        mkdir_exists(config_dir)
    return config_dir


def local_path(mkdir=True):
    root_dir = os.getcwd()
    path = os.path.join(root_dir, ".datatorch")
    if mkdir:
        mkdir_exists(path)
    return path
