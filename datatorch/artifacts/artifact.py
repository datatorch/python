from typing import Optional, Union
from uuid import UUID, uuid4

from datatorch.artifacts.commit import Commit


class ArtifactHasNoCommits(Exception):
    pass


class Artifact(object):
    @classmethod
    def create(cls, full_name: str):
        pass

    def __init__(self, name: str, tag: str = "latest") -> None:
        self.name = name
        self.tag = tag
        self.branch: str = "main"

        self._new_commit: Commit = Commit(uuid4(), artifact=self)
        self._head: Optional[Commit] = None

    def add(self, local_path: str, artifact_path: str = ""):
        self._new_commit.add(local_path, artifact_path=artifact_path)

    def remove(self, artifact_path: str):
        return self._new_commit.remove(artifact_path)

    @property
    def id(self) -> UUID:
        # TODO: get artifacts ID.
        return uuid4()

    @property
    def head(self) -> Union[Commit, None]:
        return self._head

    def commit(self, message: str = ""):
        self._new_commit.commit()

        self._head = self._new_commit
        self._new_commit = Commit(uuid4(), artifact=self)

    def download_file(self, artifact_path: str):
        if self.head:
            return self.head.download_file(artifact_path)
        raise ArtifactHasNoCommits("No commits exist for this artifact.")

    def download(self):
        if self.head:
            return self.head.download()
        raise ArtifactHasNoCommits("No commits exist for this artifact.")
