import os
import errno

from datatorch.core import env


def global_path():
    user_dir = os.path.join(os.path.expanduser("~"), ".datatorch")
    config_dir = os.getenv(env.CONFIG_DIR) or user_dir
    mkdir(config_dir)
    return config_dir


def local_path():
    root_dir = os.getcwd()
    path = os.path.join(root_dir, '.datatorch')
    mkdir(path)
    return path


def mkdir(path: str):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            return False
        else:
            raise
