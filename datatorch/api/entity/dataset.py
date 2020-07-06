from .base import BaseEntity


__all__ = "Dataset"


_CREATE_DATASET = """
    mutation CreateDataset(
      $projectId: ID!
      $name: String!
      description: String
    ) {
      dataset: createDataset(
        input: {
          projectId: $projectId
          name: $name
          description: $description
        }
      ) {
        id
      }
    }
"""


class Dataset(BaseEntity):

    id: str
    name: str
    description: str
    project_id: str
    kilobytes: int
    formatted_bytes: int
    created_at: str
    updated_at: str

    def create(self, client=None):
        super().create(client=client)

        assert self.project_id is not None
        results = self.execute(
            _CREATE_DATASET,
            params={
                "projectId": self.project_id,
                "name": self.name,
                "description": self.description,
            },
        )

        self.id = results.get("dataset").get("id")
