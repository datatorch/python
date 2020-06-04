from gql import gql
from typing import ClassVar
from .base import Entity


class Settings(Entity):
    """ Settings for the DataTorch API instance """

    api_version: ClassVar[str]
    frontend: ClassVar[str]
    api: ClassVar[str]

    def set(self, setting: str, value):
        """ Update an instance configuration property """
        raise Exception('Implementation required')

    def get(self, setting: str):
        """ Get a configuration property """
        raise Exception('Implementation required')
