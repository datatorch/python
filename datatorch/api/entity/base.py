import re
import json
import functools
from inspect import isclass

from typing import overload
from datetime import datetime

from ..client import Client

from datatorch.utils.objects import get_annotations
from datatorch.utils.string_style import camel_to_snake, snake_to_camel


class BaseEntity(object):
    @classmethod
    def add_fragment(cls, query: str, name: str = None) -> str:
        """ Appends GraphQL fragment to the query """
        return query + cls.fragment(name)

    @classmethod
    @functools.lru_cache()
    def fragment(cls, name: str = None) -> str:
        """ Creates fragment based on class annotations """

        annotations = get_annotations(cls)

        def remove_entities(kp):
            k, v = kp
            return not (isclass(v) and issubclass(v, BaseEntity))

        keys = filter(remove_entities, annotations.items())

        name = name or f"{cls.__name__}Fields"
        fragment: str = f"\nfragment {name} on {cls.__name__} {{\n"
        format_props = map(lambda p: "  " + snake_to_camel(p[0]), keys)
        fragment += "\n".join(format_props)
        fragment += "\n}\n"

        return fragment

    def __init__(self, obj: dict = {}, client: Client = None, **kwargs) -> None:

        # Init all values to None
        keys = get_annotations(self.__class__).keys()
        for key in keys:
            if key not in self.__dict__:
                self[key] = None

        # Assign values
        self._update({**camel_to_snake(obj), **kwargs})
        try:
            self.client: Client = client or Client()
        except:
            self.client = None

    def __setitem__(self, k, v):
        self.__dict__.update({k: v})

    def _update(self, obj: dict) -> None:
        self.__dict__.update(obj)

    def dict(self) -> dict:
        dic = self.__dict__.copy()
        del dic["client"]
        return dic

    def to_json(self, indent: int = 2) -> str:
        """ Format entity as json """
        return json.dumps(self.dict(), indent=indent)

    def save(self, client=None):
        if self.id is not None:
            ValueError("Entity already has an ID.")
        if client:
            self.client = client
