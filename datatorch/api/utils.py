from typing import List
from .client import Client
from .entity.base import BaseEntity


def map_entities(entities: List[object], EntityClass, client: Client = None) -> list:
    return list(map(lambda d: EntityClass(d, client), entities))


class Bulk(object):

    __slot__ = ("entities",)

    entities: List[BaseEntity]

    def add(self, entity):
        self.entities.append(entity)
        return self

    def save(self):
        pass

    def delete(self):
        pass

    def create(self):
        pass
