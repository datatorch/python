from typing import TYPE_CHECKING
from datatorch.uploader.pool import get_upload_pool
import logging

from uuid import UUID, uuid4
from pathlib import Path

logger = logging.getLogger(__name__)


class UploadEvent:
    def __init__(self):
        self.id = uuid4()

        # Number for how many times it has ran the upload command in an UploadThread.
        self.upload_count = 0

    def on_success(self):
        pass

    def on_error(self, ex: Exception):
        logger.error(ex)

    def on_done(self):
        pass

    def inc_upload_count(self):
        self.upload_count += 1

    def upload(self):
        raise NotImplementedError("Upload not implemented.")


class FileApiUploadEvent(UploadEvent):
    def __init__(self):
        from datatorch.artifacts.api import ArtifactsApi

        super().__init__()
        self._api = ArtifactsApi()


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

    def upload(self):
        self._api.upload_artifact_file(self.artifact_id, self.path, self.file_hash)


class CommitMigrationUploadEvent(FileApiPathUploadEvent):
    @classmethod
    def emit(cls, path: Path, commit_id: UUID):
        event = cls(path, commit_id)
        get_upload_pool().enqueue(event)

    def __init__(self, path: Path, commit_id: UUID):
        super().__init__(path)
        self.commit_id = commit_id

    def upload(self):
        self._api.upload_commit_migration(self.commit_id, self.path)


class CommitManifestUploadEvent(FileApiPathUploadEvent):
    @classmethod
    def emit(cls, path: Path, commit_id: UUID):
        event = cls(path, commit_id)
        get_upload_pool().enqueue(event)

    def __init__(self, path: Path, commit_id: UUID):
        super().__init__(path)
        self.commit_id = commit_id

    def upload(self):
        self._api.upload_commit_manifest(self.commit_id, self.path)


# TODO: Use TUS for resumable uploads.
class TusUploadEvent(UploadEvent):
    pass
