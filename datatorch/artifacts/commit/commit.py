import os
from os import stat_result
from uuid import UUID, uuid4
from pathlib import Path

from typing import Dict, Union

from ..hash import create_checksum
from ..api import ArtifactsApi

from .migrations import CommitMigrations
from .manifest import CommitManifest, CommitManifestFile


class CommitLockedExpection(Exception):
    pass


class _Commit(object):
    """
    Commit class access as a high level wrapper around the CommitManifest class.
    It manipulates the manifest file and adds some nice features on top of it.
    """

    @classmethod
    def from_manifest(cls, manifest_path: str):
        path = Path(manifest_path).resolve(strict=True)
        manifest = CommitManifest.load(path)
        return cls(manifest, previous_commit_id=manifest.previous_commit_id)

    def __init__(
        self,
        manifest: CommitManifest = None,
        previous_commit_id: Union[UUID, None] = None,
    ):
        self._api = ArtifactsApi()
        self.commit_id = (manifest and manifest.commit_id) or uuid4()
        self.previous_commit_id = (
            manifest and manifest.previous_commit_id
        ) or previous_commit_id
        self.manifest: CommitManifest = manifest or CommitManifest(
            self.commit_id, previous_commit_id=self.previous_commit_id
        )

    def files(self, dir: str = ""):
        dir_obj = self.manifest.get_dir(Path(dir))
        return self.manifest.files(dir_obj)

    def diff(self, commit: Union[UUID, "_Commit"] = None):
        if isinstance(commit, self.__class__):
            return self.manifest.diff(commit.manifest)

        # if isinstance(commit, UUID):
        #     # TODO: Download commit

        if self.previous_commit_id:
            return self.diff(self.previous_commit_id)

        return self.manifest.diff()

    def get(self, artifact_path: str):
        return self.manifest.get(Path(artifact_path))

    @property
    def name(self):
        return str(self.commit_id)

    @property
    def short_name(self):
        return self.name[:8]


class Commit(_Commit):
    """
    A commit that has been committed. This commit can not be modified, only
    deleted.
    """

    @classmethod
    def get(cls, commit_id: UUID):
        path = ArtifactsApi().download_commit_manifest(commit_id)
        return cls.from_manifest(str(path))

    def __init__(self, manifest: CommitManifest):
        super().__init__(manifest)

    def download(self):
        pass

    def delete(self):
        pass


class CommitActive(_Commit):
    """
    Commit that is being constructred. Once the commit is uploaded it will
    return a regular commit and the instace will not be modifiable.
    """

    def __init__(
        self,
        manifest: CommitManifest = None,
        previous_commit_id: UUID = None,
        message: str = "",
    ):
        super().__init__(manifest=manifest, previous_commit_id=previous_commit_id)
        self.message = message
        self.hashed_files: Dict[bytes, Path] = {}
        # When the commit is committed it cannot be modified.
        self._committed = False

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

    def migrations(self):
        created, deleted = self.diff(self.previous_commit_id)
        migrations = {
            **dict.fromkeys(created, "CREATED"),
            **dict.fromkeys(deleted, "DELETED"),
        }
        return CommitMigrations(
            commit_id=self.commit_id,
            migrations=migrations,
            from_commit_id=self.previous_commit_id,
        )

    def commit(self, message: str = ""):
        self.message = message
        self._committed = True

    def upload(self):
        cm = self.migrations()

        # return Commit()

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
        self.hashed_files[file_hash] = file_path
        return file_record

    def _ensure_modifiable(self):
        return True
