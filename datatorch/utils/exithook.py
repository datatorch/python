from typing import Callable

from datatorch.utils import ipython
import atexit


def register(callback: Callable, ipython_event: str = "post_execute"):
    ipython.register(ipython_event, callback) or atexit.register(callback)


def unregister(
    callback: Callable, ipython_event: str = "post_execute", silent_fail=True
):
    try:
        ipython.unregister(ipython_event, callback) or atexit.unregister(callback)
    except Exception as e:
        if not silent_fail:
            raise e
