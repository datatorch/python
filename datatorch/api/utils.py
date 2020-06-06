import re
import inspect
from typing import overload


@overload
def camel_to_snake(name: str) -> str:
    pass


@overload
def camel_to_snake(obj: dict) -> dict:
    pass


def camel_to_snake(value):
    if type(value) == str:
        value = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', value)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', value).lower()
    elif type(value) == dict:
        return {camel_to_snake(k): _process_keys(v) for k, v in value.items()}
    else:
        return value


def _process_keys(obj):
    if type(obj) == dict:
        return {camel_to_snake(k): _process_keys(v) for k, v in obj.items()}
    else:
        return obj


def snake_to_camel(value: str) -> str:
    components = value.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def get_annotations(obj: object):
    """ Returns the annotations of a class """
    members = inspect.getmembers(obj)
    for _, v in enumerate(members):
        if v[0] == '__annotations__':
            return v[1]
    return None
