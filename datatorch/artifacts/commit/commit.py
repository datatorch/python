from datatorch.artifacts.commit.migrations import CommitMigrationAction
import os
from os import stat_result
from pathlib import Path
from typing import Dict

from datatorch.artifacts.hash import create_checksum
from .manifest import CommitManifest, CommitManifestFile


class _Commit(object):
    def __init__(self, manifest_path: str = None, previous: "_Commit" = None):
        self.previous = previous
        self.manifest: CommitManifest = (
            CommitManifest.load(Path(manifest_path))
            if manifest_path
            else CommitManifest()
        )

    def files(self, dir: str = ""):
        dir_obj = self.manifest.get_dir(Path(dir))
        return self.manifest.files(dir_obj)

    def diff(self, commit: "_Commit" = None):
        commit_to_diff = commit or self.previous
        return self.manifest.diff(commit_to_diff and commit_to_diff.manifest)


def Commit(_Commit):
    def download(self):
        pass


class CommitActive(_Commit):
    def __init__(self, previous: "_Commit" = None):
        super().__init__(previous=previous)
        self.hashed_files: Dict[bytes, Path] = {}

    def __setitem__(self, artifact_path: str, local_path: str):
        if not self.add(local_path, artifact_path=artifact_path):
            raise FileExistsError(f"File or directory not found ({local_path}).")

    def add(self, local_path: str, artifact_path: str = ""):
        path_local = Path(local_path).resolve(strict=False)

        if path_local.is_file():
            self.add_file(local_path, artifact_path=artifact_path)
            return True

        if path_local.is_dir():
            self.add_dir(local_path, artifact_path=artifact_path)
            return True
        # TODO: add support for regex as inputs. e.g ./examples/**/*.png
        return False

    def add_file(self, local_path: str, artifact_path: str = ""):
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
        path = Path(local_path).resolve(strict=True)

        if not path.is_dir():
            raise ValueError(f"Local path: '{local_path}' must be a directory.")

        for file in path.rglob(pattern):
            if file.is_file():
                ap = os.path.join(artifact_path, file.relative_to(path))
                self.add_file(str(file), artifact_path=ap)

    def __delitem__(self, artifact_path: str):
        path_exists = self.manifest.get(Path(artifact_path))
        if not path_exists:
            raise KeyError(f"'{artifact_path}' does not exist in this commit.")
        self.remove(artifact_path)

    def remove(self, artifact_path):
        self.manifest.remove(Path(artifact_path))

    def upload(self):
        created, deleted = self.diff()

        migrations = {
            **dict.fromkeys(created, CommitMigrationAction.Created),
            **dict.fromkeys(deleted, CommitMigrationAction.Deleted),
        }
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
