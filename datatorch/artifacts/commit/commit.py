import os
from datatorch.artifacts.hash import create_checksum
from pathlib import Path
from .manifest import CommitManifest, CommitManifestFile


class Commit(object):
    def schema(self):
        pass

    def __init__(self, manifest_path: str = None):
        self.frozen = manifest_path is not None
        self.manifest: CommitManifest = (
            CommitManifest.load(Path(manifest_path))
            if manifest_path
            else CommitManifest()
        )

    def __setitem__(self, artifact_path: str, local_path: str):
        path_local = Path(local_path).resolve(strict=False)

        if path_local.is_file():
            self.add_file(local_path, artifact_path=artifact_path)
            return

        if path_local.is_dir():
            self.add_dir(local_path, artifact_path=artifact_path)
            return

        raise FileExistsError(f"Unknown file or directory ({local_path}).")

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

        file_hash = create_checksum(str(path))
        file_record: CommitManifestFile = {
            "hash": file_hash,
            "size": lstat.st_size,
            "lastModified": lstat.st_mtime,
        }

        # Add file to manifest
        self.manifest[artifact_path] = file_record
        return True

    def remove_file(self, artifact_path):
        pass

    def add_dir(self, local_path: str, artifact_path: str = "", pattern: str = "*"):
        path = Path(local_path).resolve(strict=True)

        if not path.is_dir():
            raise ValueError(f"Local path: '{local_path}' must be a directory.")

        for file in path.rglob(pattern):
            if file.is_file():
                ap = os.path.join(artifact_path, file.relative_to(path))
                self.add_file(str(file), artifact_path=ap)

    def upload(self):
        pass