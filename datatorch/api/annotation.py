from typing import List

from .base import BaseEntity
from .sources.source import Source


class Annotation(BaseEntity):

    id: str
    name: str
    color: str
    file_id: str
    label_id: str
    sources_json: List[dict]

    @property
    def sources(self) -> List[Source]:
        return list(map(lambda s: Source(s, self.client), self.sources_json))

    def add(self, source: Source):
        if self.id:
            # Create
            pass
        if self.sources_json is None:
            self.sources_json = []
        self.sources_json.append(source.__dict__)
