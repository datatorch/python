import os
import errno


def mkdir_exists(path: str) -> None:
    """Creates directories if they do not exist.

    Args:
        path (str): string of directories to create

    Returns:
        None
    """
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            return
        else:
            raise
