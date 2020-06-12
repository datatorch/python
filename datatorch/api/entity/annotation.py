from typing import List

from datatorch.utils import camel_to_snake
from ..utils import map_entities
from .base import BaseEntity
from .label import Label
from .sources.source import Source


__all__ = "Annotation"


_CREATE_ANNOTATION = """
  mutation AddAnnotation(
    $id: ID
    $fileId: ID!
    $name: String
    $labelId: ID!
    $color: String
  ) {
    annotation: createAnnotation(
      id: $id
      fileId: $fileId
      name: $name
      labelId: $labelId
      color: $color
    ) {
      id
      fileId
      color
    }
  }
"""


class Annotation(BaseEntity):

    id: str
    name: str
    color: str
    file_id: str
    label_id: str
    sources_json: List[dict]
    sources = []

    def __init__(self, obj={}, client=None, label: Label = None, **kwargs):
        super().__init__(obj=obj, client=client, **kwargs)
        if label:
            self.label(label)

    def _update(self, obj: dict):
        self.sources = map_entities(
            obj.get("sources_json", []), Source, client=self.client
        )
        obj.pop("sources_json", None)
        super()._update(obj)

    def add(self, source: Source) -> None:
        self.sources.append(source)

        if self.id:
            source.annotation_id = self.id
            source.save(client=self.client)

    def label(self, label: Label) -> None:
        self.label_id = label.id

    def create(self, client=None):
        super().create(client=client)

        assert self.label_id is not None, "Annotation must have a file ID"
        assert self.file_id is not None, "Annotation must have label ID"

        params = {
            "id": self.id,
            "fileId": self.file_id,
            "name": self.name,
            "labelId": self.label_id,
            "color": self.color,
        }
        results = self.client.execute(_CREATE_ANNOTATION, params=params)
        r_anno = results.get("annotation")
        self.__dict__.update(camel_to_snake(r_anno))

        for source in self.sources:
            source.annotation_id = self.id
            source.create(client=self.client)
