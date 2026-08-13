from .base import BaseEntity

__all__ = "Dataset"


_FORK_DATASET = """
    mutation ForkDataset(
      $datasetId: ID!
      $branchName: String!
      $versionId: ID
    ) {
      fork: forkDataset(
        datasetId: $datasetId
        branchName: $branchName
        versionId: $versionId
      ) {
        dataset {
          id
          name
          description
          projectId
          branchName
          parentDatasetId
          forkedAt
        }
      }
    }
"""


_CREATE_DATASET = """
    mutation CreateDataset(
      $projectId: ID!
      $name: String!
      $description: String
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
        results = self.client.execute(
            _CREATE_DATASET,
            params={
                "projectId": self.project_id,
                "name": self.name,
                "description": self.description,
            },
        )

        self.id = results.get("dataset").get("id")

    def fork(self, branch_name: str, version_id: str = None, client=None):
        """
        Forks this dataset into a branch and returns it as a new Dataset.

        The branch shares the parent's storage objects and copies its
        annotations. Pass `version_id` to start the branch from a version's
        reconstructed state instead of the live state. The returned dataset
        can be used anywhere a dataset id is accepted (e.g. uploads).

        Note: branch attributes (`branch_name`, `parent_dataset_id`,
        `forked_at`) are set dynamically on the returned instance; they are
        deliberately kept out of the class annotations so the generated
        `DatasetFields` fragment stays compatible with servers that predate
        branching.
        """
        assert self.id is not None
        if client:
            self.client = client
        assert self.client is not None

        results = self.client.execute(
            _FORK_DATASET,
            params={
                "datasetId": self.id,
                "branchName": branch_name,
                "versionId": version_id,
            },
        )
        return Dataset(results.get("fork").get("dataset"), client=self.client)
