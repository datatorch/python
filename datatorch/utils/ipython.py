from typing import Any, Callable, Union


def get_ipython() -> Union[Any, None]:
    try:
        import IPython as ip

        return ip.get_ipython()
    except ImportError:
        return False


def register(event: str, callback: Callable):
    ip = get_ipython()
    if ip:
        ip.events.register(event, callback)
        return True
    return False


def unregister(event: str, callback: Callable):
    ip = get_ipython()
    if ip:
        ip.events.unregister(event, callback)
        return True
    return False
