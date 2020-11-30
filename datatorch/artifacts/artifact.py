import functools
from typing import Optional, Union
from uuid import UUID, uuid4

from .commit.commit import CommitStatus
from .commit import Commit
from .api import ArtifactsApi


_api = ArtifactsApi()


class InvalidArtifactName(Exception):
    pass


class ArtifactHasNoCommits(Exception):
    pass


class Artifact(object):
    @classmethod
    def create(cls, full_name: str):
        pass

    def __init__(self, full_name: str, tag: str = "latest") -> None:
        global _api
        self._api = _api

        self.tag = tag
        self.branch: str = "main"

        if len(full_name.split("/")) != 3:
            raise InvalidArtifactName(
                "An artifact is made up of three parts. The owner which "
                + "is your login or an organizations slug, the project "
                + "slug, and the name of the artifact. These need to be "
                + "seperated by forward splash's (/)."
            )

        self.namespace, self.project_name, self.name = full_name.split("/")

        self._new_commit: Commit = Commit(
            uuid4(), status=CommitStatus.Initalized, artifact=self
        )
        self._head: Optional[Commit] = None

    def add(self, local_path: str, artifact_path: str = ""):
        self._new_commit.add(local_path, artifact_path=artifact_path)

    def remove(self, artifact_path: str):
        return self._new_commit.remove(artifact_path)

    @functools.lru_cache()
    def __entity(self):
        return self._api.artifact_by_name(self.namespace, self.project_name, self.name)

    @property
    def id(self) -> UUID:
        return UUID(self.__entity().get("id"))

    @property
    def head(self) -> Union[Commit, None]:
        return self._head

    def commit(self, message: str = ""):
        self._new_commit.commit()

        self._head = self._new_commit
        self._new_commit = Commit(
            uuid4(), status=CommitStatus.Initalized, artifact=self
        )

    def download_file(self, artifact_path: str):
        if self.head:
            return self.head.download_file(artifact_path)
        raise ArtifactHasNoCommits("No commits exist for this artifact.")

    def download(self):
        if self.head:
            return self.head.download()
        raise ArtifactHasNoCommits("No commits exist for this artifact.")
