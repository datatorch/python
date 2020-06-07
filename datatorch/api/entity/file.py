from typing import List

import json

from ..utils import map_entities
from .base import BaseEntity
from .annotation import Annotation

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


class File(BaseEntity):
    @classmethod
    def fragment(cls, name=None):
        # Custom fragment to pull annotations with file.
        name = name or f"{cls.__name__}Fields"
        return Annotation.add_fragment(
            f"""
            \nfragment {name} on {cls.__name__} {{
              id
              name
              path
              mimetype
              encoding
              kilobytes
              url
              ... on DatasetFile {{
                status
                datasetId
                annotationsCount
                annotations {{
                  ...AnnotationFields
                }}
              }}
            }}\n
            """
        )

    id: str
    name: str
    path: str
    mimetype: str
    encoding: str
    kilobytes: str
    url: str
    status: str
    dataset_id: str
    annotation_count: int
    annotations: List[Annotation]

    def add(self, anno: Annotation) -> None:
        """Add annotation to file.

        Args:
            anno (:obj:`Annotation`): annotation to be added
        """
        self.annotations.append(anno)

        if self.id is None:
            anno.file_id = self.id
            anno.save(client=self.client)

    def _update(self, obj):
        self.annotations = map_entities(
            obj.get("annotations", []), Annotation, client=self.client
        )
        obj.pop("annotations", None)
        super()._update(obj)

    def annotator(self):
        """ Opens file in annotator """
        import webbrowser

        url = self.client.api_url.replace("/api", f"/annotate/{self.id}")
        webbrowser.open(url)

    def to_json(self, indent: int = 2) -> str:
        dic = self.__dict__.copy()
        dic.pop("client")
        dic["annotations"] = [anno.__dict__ for anno in dic["annotations"]]
        return json.dumps(dic, indent=indent)
