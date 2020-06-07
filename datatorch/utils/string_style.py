import re
from typing import Callable, Any, Union


def camel_to_snake(value: Union[str, dict]) -> Union[str, dict]:
    """Converts camel to snake case

    When applied to a `dict` only keys will be effected.

    Args:
        value (Union[str, dict]): [description]

    Returns:
        Union[str, dict]: [description]
    """
    if type(value) == str:
        value = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", value)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", value).lower()
    if type(value) == dict:
        return _process_keys(value, camel_to_snake)


def snake_to_camel(value: Union[str, dict]) -> Union[str, dict]:
    """Converts snake to camel case

    When applied to a `dict` only keys will be effected

    Args:
        value: [description]

    Returns:
        input in converted format
    """
    if type(value) == str:
        components = value.split("_")
        return components[0] + "".join(x.title() for x in components[1:])
    if type(value) == dict:
        return _process_keys(value, snake_to_camel)


def _process_keys(obj: Any, func: Callable[[str], str]):
    if type(obj) == dict:
        return {func(k): _process_keys(v, func) for k, v in obj.items()}
    else:
        return obj
