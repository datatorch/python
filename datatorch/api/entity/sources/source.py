from ..base import BaseEntity
from datatorch.utils import snake_to_camel


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
      annotationId
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

    def save(self, client=None):
        super().create(client=client)
