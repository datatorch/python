from typing import List, Union

from .dataset import Dataset
from .label import Label
from .base import BaseEntity
from .storage_link import StorageLink

_DATASETS = Dataset.add_fragment(
    """
    query ProjectDatasets($projectId: ID!) {
      project: projectById(id: $projectId) {
        datasets {
          nodes {
            ...DatasetFields
          }
        }
      }
    }
    """
)

_LABELS = Label.add_fragment(
    """
    query GetProjectLabels($projectId: ID!) {
      project: projectById(id: $projectId) {
        labels {
          ...LabelFields
        }
      }
    }
    """
)

_STORAGE_LINKS = StorageLink.add_fragment(
    """
    query GetStorageLinks($projectId: ID!) {
      project: projectById(id: $projectId) {
        storageLinks {
          ...StorageLinkFields
        }
      }
    }
    """
)

AddableEntity = Union[Dataset, Label]


class Project(BaseEntity):
    """ Projects contain datasets, files and annotations. """

    id: str
    slug: str
    name: str
    description: str
    visibility: str
    about: str
    owner_id: str
    namespace: str
    path: str
    path_with_spaces: str
    avatar_url: str
    is_private: bool
    kilobytes: int
    formatted_bytes: str
    is_archived: bool
    created_at: str
    updated_at: str

    def datasets(self) -> List[Dataset]:
        return self.client.query_to_class(
            Dataset,
            _DATASETS,
            path="project.datasets.nodes",
            params={"projectId": self.id},
        )

    def labels(self) -> List[Label]:
        return self.client.query_to_class(
            Label, _LABELS, path="project.labels", params={"projectId": self.id}
        )

    def storage_links(self) -> List[StorageLink]:
        params = {"projectId": self.id}
        return self.client.query_to_class(
            StorageLink, _STORAGE_LINKS, path="project.storageLinks", params=params
        )

    def add(self, entity: AddableEntity):
        """ Add entity to project """

        entity.client = self.client

        if isinstance(entity, Dataset):

            # results = self.client.execute(ADD_DATASET, params={
            #     'projectId': self.id, 'name': entity.name, 'description': entity.description
            # })
            # entity.__dict__.update(results.get('createDataset'))
            return

        if isinstance(entity, Label):
            self.create
