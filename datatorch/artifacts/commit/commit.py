from datatorch.artifacts.downloader.pool import download_commit
from enum import Enum
from datatorch.uploader.events import CommitMigrationUploadEvent
import os
import functools
from pathlib import Path
from os import stat, stat_result
from uuid import UUID, uuid4
from typing import Dict, Optional, Union, TYPE_CHECKING, cast

from ..hash import create_checksum
from ..api import ArtifactsApi
from ..directory import ArtifactDirectory

from .migrations import CommitMigrations
from .manifest import CommitManifest, CommitManifestFile

from datatorch.uploader import CommitManifestUploadEvent, ArtifactFileUploadEvent


if TYPE_CHECKING:
    from ..artifact import Artifact


class CommitLockedExpection(Exception):
    """ Rased when trying to modify a commit that has been committed. """

    pass


class CommitNotUploadedExpection(Exception):
    """
    Raised when trying to download a commit that hasn't successfully
    uploaded.
    """

    pass


class CommitMissingArtifact(Exception):
    pass


class CommitStatus(Enum):
    Uploading = "UPLOADING"
    Initalized = "INITALIZED"
    Failed = "FAILED"
    Committed = "COMMITTED"
    Deleted = "DELETED"

    def __eq__(self, o) -> bool:
        return str(o) == str(self)
    
    def __str__(self):
        return self.value


class Commit:
    def __init__(
        self,
        commit_id: UUID,
        message: str = "",
        artifact: "Artifact" = None,
        previous: "Optional[Commit]" = None,
        status: CommitStatus = CommitStatus.Initalized,
    ):
        self.id = commit_id
        self.message = message
        self.artifact = artifact
        self.previous = previous
        self.__status = status

        self.message = message
        self.artifact: "Optional[Artifact]" = artifact

        self._api = ArtifactsApi()

        # Store files that are hashed so we can get there paths when we upload.
        self.hashed_files: Dict[str, Path] = {}

    @functools.lru_cache()
    def load_manifest(self) -> CommitManifest:
        try:
            path = self._api.download_commit_manifest(self.id)
            return CommitManifest.load(path)
        except (FileNotFoundError, ValueError):
            if self.is_committed:
                raise           

        previous_id = self.previous and self.previous.id
        return CommitManifest(commit_id=self.id, previous_commit_id=previous_id)

    @property
    def is_committed(self):
        return self.__status == CommitStatus.Committed

    @property
    def is_uploading(self):
        return self.__status == CommitStatus.Uploading

    @property
    def manifest(self):
        return self.load_manifest()

    @property
    def manifest_path(self):
        return Path(ArtifactDirectory().commit_manifest(self.id))

    @property
    def migration_path(self):
        return Path(ArtifactDirectory().commit_migration(self.id))

    @property
    def name(self):
        return str(self.id)

    @property
    def short_name(self):
        return self.name[:8]

    def download_file(self, artifact_path: str) -> str:
        self._ensure_downloadable()

        return ""

    def download(self, wait=True):
        self._ensure_downloadable()
        download_commit(self, wait=wait)
        return ""

    def files(self, dir: str = ""):
        dir_obj = self.manifest.get_dir(Path(dir))
        return self.manifest.files(dir_obj)

    def get(self, artifact_path: str):
        return self.manifest.get(Path(artifact_path))

    def __setitem__(self, artifact_path: str, local_path: str):
        if not self.add(local_path, artifact_path=artifact_path):
            raise FileExistsError(f"File or directory not found ({local_path}).")

    def add(self, local_path: str, artifact_path: str = ""):
        self._ensure_modifiable()
        path_local = Path(local_path).resolve(strict=False)

        if path_local.is_file():
            self.add_file(local_path, artifact_path=artifact_path)
            return True

        if path_local.is_dir():
            self.add_dir(local_path, artifact_path=artifact_path)
            return True

        # TODO: Allow regex for absolute paths
        return self.add_dir(".", artifact_path=artifact_path, pattern=local_path)

    def add_file(self, local_path: str, artifact_path: str = ""):
        self._ensure_modifiable()

        path = Path(local_path).resolve(strict=True)
        path_artifact = Path(artifact_path or path.name)

        if not path.is_file():
            raise ValueError(f"Path is not a file. '{local_path}' must be a file.")

        lstat = path.lstat()
        manifest_file = self.manifest.get_file(path_artifact)
        if (
            manifest_file is not None
            and manifest_file["lastModified"] == lstat.st_mtime
            and manifest_file["size"] == lstat.st_size
        ):
            # File is already exists and it hasn't changed.
            return False

        # Expensive operation. Best to not run it unless we have to
        record = self._hash_file(path, lstat=lstat)
        return self.manifest.add(path_artifact, record)

    def add_dir(self, local_path: str, artifact_path: str = "", pattern: str = "*"):
        self._ensure_modifiable()

        path = Path(local_path).resolve(strict=True)
        if not path.is_dir():
            raise ValueError(f"Local path: '{local_path}' must be a directory.")

        for file in path.rglob(pattern):
            if file.is_file():
                ap = os.path.join(artifact_path, file.relative_to(path))
                self.add_file(str(file), artifact_path=ap)

    def __delitem__(self, artifact_path: str):
        self._ensure_modifiable()

        path_exists = self.manifest.get(Path(artifact_path))
        if not path_exists:
            raise KeyError(f"'{artifact_path}' does not exist in this commit.")
        self.remove(artifact_path)

    def remove(self, artifact_path):
        self._ensure_modifiable()
        self.manifest.remove(Path(artifact_path))

    def diff(self, commit: "Commit" = None):
        return self.manifest.diff(commit and commit.manifest)

    def migrations(self):
        created, deleted = self.diff(self.previous)
        migrations = {
            **dict.fromkeys(created, "CREATED"),
            **dict.fromkeys(deleted, "DELETED"),
        }
        return CommitMigrations(
            commit_id=self.id,
            migrations=migrations,
            from_commit_id=self.previous and self.previous.id,
        )

    def commit(self, message: str = ""):
        """
        Creates commit entity, and sends files to thread pool to be
        uploaded.
        """
        self._ensure_artifact()
        self._ensure_modifiable()

        self.__status = CommitStatus.Uploading
        self.message = message or self.message

        artifact: "Artifact" = self.artifact  # type: ignore

        # TODO: GraphQL Commit create call

        # Write and upload manifest.
        self.manifest.write(self.manifest_path)
        CommitManifestUploadEvent.emit(self.manifest_path, self.id)

        # Write and upload migrations.
        migrations = self.migrations()
        migrations.write(self.migration_path)
        CommitMigrationUploadEvent.emit(self.migration_path, self.id)
        for i, b in self.files():
            print(i, b['hash'].hex())
        # Create an upload event for each new file create
        migrations = self.migrations().migrations
        for hash, action in migrations.items():
            if action == "CREATED":
                print(action, hash)
                path = self.hashed_files[hash]
                ArtifactFileUploadEvent.emit(
                    path, artifact_id=artifact.id, file_hash=hash
                )
            if action == "DELETED":
                # Just because a file is deleted from a commit does not mean we
                # can delete it on the server. It may be used in other commits.
                continue

    def _hash_file(
        self, file_path: Path, lstat: stat_result = None
    ) -> CommitManifestFile:
        lstat = lstat or file_path.lstat()
        file_hash = create_checksum(str(file_path))
        file_record: CommitManifestFile = {
            "hash": file_hash,
            "size": lstat.st_size,
            "lastModified": lstat.st_mtime,
        }
        self.hashed_files[file_hash.hex()] = file_path
        return file_record

    def _ensure_artifact(self):
        if not self.artifact:
            raise CommitMissingArtifact(
                "This commit is missing the an artifact. You "
                + "can assign an artifact using the `artifact` "
                + "property."
            )

    def _ensure_modifiable(self):
        if self.__status != CommitStatus.Initalized:
            raise CommitLockedExpection(
                "This commit has been committed. You can not "
                + "modify it anymore. You can branch from this "
                + "commmit or create a new one to the head of "
                + "the artifact."
            )

    def _ensure_downloadable(self):
        if self.__status != CommitStatus.Committed:
            pass
