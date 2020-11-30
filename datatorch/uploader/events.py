import logging
from typing import Optional, TYPE_CHECKING

from datatorch.utils.thread_pool import ThreadJob
from datatorch.uploader.pool import get_upload_pool

from uuid import UUID
from pathlib import Path


if TYPE_CHECKING:
    from datatorch.artifacts.api import ArtifactsApi


logger = logging.getLogger(__name__)


__artifact_api: "Optional[ArtifactsApi]" = None


def _artifact_api():
    global __artifact_api

    if __artifact_api is None:
        from datatorch.artifacts.api import ArtifactsApi

        __artifact_api = ArtifactsApi.instance()
    return __artifact_api


class FileApiUploadEvent(ThreadJob):
    def __init__(self):
        self._api = _artifact_api()
        super().__init__()


class FileApiPathUploadEvent(FileApiUploadEvent):
    def __init__(self, path: Path):
        super().__init__()

        if not path.is_file():
            raise ValueError("Path must point to a file.")
        self.path = path


class ArtifactFileUploadEvent(FileApiPathUploadEvent):
    @classmethod
    def emit(cls, path: Path, artifact_id: UUID, file_hash: str):
        event = cls(path, artifact_id, file_hash)
        get_upload_pool().enqueue(event)

    def __init__(self, path: Path, artifact_id: UUID, file_hash: str):
        super().__init__(path)
        self.artifact_id = artifact_id
        self.file_hash = file_hash

    def run(self):
        self._api.upload_artifact_file(self.artifact_id, self.path, self.file_hash)


class CommitMigrationUploadEvent(FileApiPathUploadEvent):
    @classmethod
    def emit(cls, path: Path, commit_id: UUID):
        event = cls(path, commit_id)
        get_upload_pool().enqueue(event)

    def __init__(self, path: Path, commit_id: UUID):
        super().__init__(path)
        self.commit_id = commit_id

    def run(self):
        self._api.upload_commit_migration(self.commit_id, self.path)


class CommitManifestUploadEvent(FileApiPathUploadEvent):
    @classmethod
    def emit(cls, path: Path, commit_id: UUID):
        event = cls(path, commit_id)
        get_upload_pool().enqueue(event)

    def __init__(self, path: Path, commit_id: UUID):
        super().__init__(path)
        self.commit_id = commit_id

    def run(self):
        self._api.upload_commit_manifest(self.commit_id, self.path)


# TODO: Use TUS for resumable uploads.
class TusUploadEvent(ThreadJob):
    pass
