from typing import List

import json

from datatorch.utils import camel_to_snake

from ..utils import map_entities
from .base import BaseEntity
from .annotation import Annotation


__all__ = "File"


_CREATE_FILE = """
  mutation ImportFile(
    $linkId: ID!
    $datasetId: ID
    $importFile: ImportFile!
  ) {
    file: importFiles(
      linkId: $linkId
      files: [$importFile]
      datasetId: $datasetId
    ) {
      id
      name
      path
      mimetype
      linkId
    }
  }
"""


class File(BaseEntity):
    @classmethod
    def add_fragment(cls, query, name=None, data_file=False):
        return query + cls.fragment(name, data_file)

    @classmethod
    def fragment(cls, name=None, data_file=False):
        # Custom fragment to pull annotations with file.
        name = name or f"{cls.__name__}Fields"

        all_file_props = """
          id
          linkId
          name
          path
          mimetype
          encoding
          kilobytes
          url
        """

        data_file_props = """
          status
          datasetId
          annotationsCount
          annotations {
            ...AnnotationFields
          }
        """

        if data_file:
            return Annotation.add_fragment(
                f"""
                \nfragment {name} on DatasetFile {{
                  {all_file_props}
                  {data_file_props}
                }}
                """
            )

        return Annotation.add_fragment(
            f"""
            \nfragment {name} on {cls.__name__} {{
                {all_file_props}
                ... on DatasetFile {{
                    {data_file_props}
                }}
            }}\n
            """
        )

    id: str
    name: str
    path: str
    link_id: str
    mimetype: str
    encoding: str
    kilobytes: str
    url: str
    status: str
    dataset_id: str
    annotation_count: int
    annotations: List[Annotation]

    def create(self, client=None) -> None:
        """ Imports file """
        super().create(client=client)

        assert self.link_id is not None
        assert self.path is not None

        results = self.client.execute(
            _CREATE_FILE,
            params={
                "linkId": self.link_id,
                "datasetId": self.dataset_id,
                "importFile": {
                    "path": self.path,
                    "name": self.name,
                    "size": self.kilobytes * 1024,
                },
            },
        )

        r_file = results.get("file")
        self.__dict__.update(camel_to_snake(r_file))

    def add(self, anno: Annotation) -> None:
        """Add annotation to file.

        Args:
            anno (:obj:`Annotation`): annotation to be added
        """
        self.annotations.append(anno)
        if self.id is not None:
            anno.file_id = self.id
            anno.create(client=self.client)

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
        dic["annotations"] = [anno.to_json() for anno in dic["annotations"]]
        return json.dumps(dic, indent=indent)
