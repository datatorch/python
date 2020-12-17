from ..base import BaseEntity
from datatorch.utils import snake_to_camel


__all__ = "Source"


_CREATE_SOURCE = """
  mutation AddSource(
    $id: ID
    $annotationId: ID!
    $type: String!
    $data: JSON
  ) {
    source: createSource(
      id: $id
      annotationId: $annotationId
      type: $type
      data: $data
    ) {
      id
    }
  }
"""

_UPDATE_SOURCE = """
  mutation UpdateSource(
    $id: ID!
    $type: String!
    $data: JSON!
  ) {
    source: updateSource(
      id: $id
      type: $type
      data: $data
    ) {
      id
    }
  }
"""

class Source(BaseEntity):

    id: str
    type: str
    annotation_id: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = self.type or self.__class__.type

    def data(self):
        obj = self.dict()
        del obj["id"]
        del obj["type"]
        del obj["annotation_id"]
        return dict([(snake_to_camel(k), v) for k, v in obj.items()])

    def create(self, client=None):
        super().create(client=client)

        assert self.type is not None, "Source must have a type"
        results = self.client.execute(
            _CREATE_SOURCE,
            params={
                "id": self.id,
                "annotationId": self.annotation_id,
                "type": self.type,
                "data": self.data(),
            },
        )
        r_source = results.get("source")
        self.id = r_source.get("id")

    def save(self, client=None):
      super().save(client=client)

      assert self.type is not None, "Source must have a type"
      self.client.execute(
          _UPDATE_SOURCE,
          params={
              "id": self.id,
              "type": self.type,
              "data": self.data(),
          },
      )
