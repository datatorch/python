from typing import List, Union

from ..where import Where
from .dataset import Dataset
from .label import Label
from .base import BaseEntity
from .file import File
from .storage_link import StorageLink

from typing import cast

__all__ = "Project"


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

_DATASET_FILES = File.add_fragment(
    """
    query GetProjectFiles(
      $projectId: ID!
      $where: DatasetFileWhereInput
      $page: Int
      $perPage: Int
    ) {
      project: projectById(id: $projectId) {
        files(input: { where: $where, perPage: $perPage, page: $page }) {
          nodes {
            ...FileFields
          }
        }
      }
    }
    """,
    data_file=True,
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
        return cast(
            List[Dataset],
            self.client.query_to_class(
                Dataset,
                _DATASETS,
                path="project.datasets.nodes",
                params={"projectId": self.id},
            ),
        )

    def files(self, where: Where = None, limit=500, page=1) -> List[File]:
        if where is None:
            where = Where()
        return cast(
            List[File],
            self.client.query_to_class(
                File,
                _DATASET_FILES,
                path="project.files.nodes",
                params={
                    "projectId": self.id,
                    "perPage": limit,
                    "page": page,
                    "where": where.input,
                },
            ),
        )

    def labels(self) -> List[Label]:
        return cast(
            List[Label],
            self.client.query_to_class(
                Label, _LABELS, path="project.labels", params={"projectId": self.id}
            ),
        )

    def storage_links(self) -> List[StorageLink]:
        return cast(
            List[StorageLink],
            self.client.query_to_class(
                StorageLink,
                _STORAGE_LINKS,
                path="project.storageLinks",
                params={"projectId": self.id},
            ),
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
