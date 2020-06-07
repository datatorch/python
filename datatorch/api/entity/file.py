from typing import List

import json
import functools

from datatorch.utils.string_style import camel_to_snake
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

    @property
    @functools.lru_cache()
    def annotations(self):
        return list(map(lambda a: Annotation(a, self.client), self._annotations))

    def add(self, anno: Annotation) -> None:
        """ Add annotation to file """
        anno.client = self.client
        anno.save()
        self._annotations.append(anno.__dict__)

    def remove(self, id: str) -> None:
        pass

    def download(self, path: str = None, annotations: bool = True):
        pass

    def _update(self, obj):
        self.annotations = list(
            map(lambda a: Annotation(a, self.client), obj["annotations"])
        )
        del obj["annotations"]
        super()._update(obj)

    def to_json(self, indent: int = 2) -> str:
        dic = self.__dict__.copy()
        del dic["client"]
        dic["annotations"] = self._annotations
        del dic["_annotations"]
        return json.dumps(dic, indent=indent)
