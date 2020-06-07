from typing import List

from datatorch.utils.string_style import camel_to_snake
from .base import BaseEntity
from .label import Label
from .sources.source import Source

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

    def __init__(self, obj={}, client=None, label: Label = None, **kwargs):
        super().__init__(obj=obj, client=client, **kwargs)
        if label:
            self.label(label)

    @property
    def sources(self) -> List[Source]:
        print(self.sources_json)
        return list(map(lambda s: Source(s, self.client), self.sources_json or []))

    def add(self, source: Source) -> None:
        if self.sources_json is None:
            self.sources_json = []
        self.sources_json.append(source.__dict__)

    def label(self, label: Label) -> None:
        self.label_id = label.id

    def save(self, client=None):
        super().save(client=client)

        if self.label_id is None:
            raise ValueError("Annotation does not have a label ID.")
        if self.file_id is None:
            raise ValueError("Annotation does not have a file ID.")

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
            source.save(client=self.client)
            params = {
                "id": source.id,
                "annotationId": self.id,
                "type": source.type,
                "data": source.data(),
            }
            results = self.client.execute(_CREATE_SOURCE, params=params)
            source.__dict__.update(camel_to_snake(results.get("source")))
            source.client = self.client
