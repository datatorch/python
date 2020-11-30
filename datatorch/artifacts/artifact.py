import functools
from typing import List, Optional, Union
from uuid import UUID, uuid4

from .api import ArtifactExistsError, ArtifactsApi
from .commit.commit import CommitStatus
from .commit import Commit


class InvalidArtifactName(Exception):
    pass


class ArtifactHasNoCommits(Exception):
    pass


class Artifact(object):
    @classmethod
    def create(cls, full_name: str):
        pass

    def __init__(self, full_name: Union[str, UUID], tag: str = "latest") -> None:

        if isinstance(full_name, UUID):
            raise ValueError("TODO")

        self._api = ArtifactsApi.instance()
        self._artifact_id = id
        self.tag = tag

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
    def __get_entity(self):
        try:
            return self._api.artifact_by_name(self.namespace, self.project_name, self.name)
        except ArtifactExistsError:
            # return self._api.create_artifact(self.namespace, self.project_name, self.name)
            pass
    
    @functools.lru_cache()
    def __get_commit(self, commit_id: UUID) -> Optional[Commit]:
        commit = Commit.request(commit_id)
        commit.artifact = self
        return commit

    @property
    def head(self) -> Optional[Commit]:
        if self.tag == "latest":
            entity = self.__get_entity()
            commit_entity = entity.get("latest")
            if not commit_entity:
                return None
            commit = Commit.from_dict(commit_entity)
            commit.artifact = self
            return commit

        # TODO: get head when a tag is provided

    @property
    def id(self) -> UUID:
        return UUID(self.__get_entity().get("id"))

    def commit(self, message: str = "", tags: List[str] = []):
        self._new_commit.commit(message=message, tags=tags)

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
