# from __future__ import annotations
import re
import json

from typing import overload
from datetime import datetime


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


class Entity(object):
    def __init__(self, client: object, obj: dict):
        self._client = client
        self.__dict__.update(camel_to_snake(obj))

    def to_json(self, indent: int = 2) -> str:
        dic = self.__dict__
        del dic['_client']
        return json.dumps(dic, indent=indent)


class TimestampEntity(Entity):

    def created_at(self) -> datetime:
        pass

    def updated_at(self) -> datetime:
        pass
