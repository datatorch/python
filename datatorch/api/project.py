from gql import gql
from typing import ClassVar, List

from .dataset import Dataset
from .label import Label
from .base import Entity


GET_PROJECT_DATASET = gql("""
    query GetProjectDatasets($projectId: ID!) {
      project: projectById(id: $projectId) {
        datasets {
          nodes {
            id
            name
            description
            projectId
            kilobytes
            formattedBytes
            createdAt
            updatedAt
          }
        }
      }
    }
""")


class Project(Entity):
    """ Projects contain datasets, files and annotations. """

    id: ClassVar[str]
    slug: ClassVar[str]
    name: ClassVar[str]
    description: ClassVar[str]
    visibility: ClassVar[str]
    about: ClassVar[str]
    owner_id: ClassVar[str]
    namespace: ClassVar[str]
    path: ClassVar[str]
    path_with_spaces: ClassVar[str]
    avatar_url: ClassVar[str]
    is_private: ClassVar[bool]
    kilobytes: ClassVar[int]
    formatted_bytes: ClassVar[str]
    is_archived: ClassVar[bool]
    created_at: ClassVar[str]
    updated_at: ClassVar[str]

    def create_dataset(self, name: str, description: str = None):
        pass

    def datasets(self) -> List[Dataset]:
        params = {'projectId': self.id}
        results = self._client.execute(GET_PROJECT_DATASET, params=params)
        datasets = results.get('project').get('datasets').get('nodes')
        return list(map(lambda d: Dataset(self._client, d), datasets))

    def labels(self) -> List[Label]:
        pass

    def label(self, id) -> List[Label]:
        pass
