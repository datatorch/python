from pathlib import Path
from typing import Any, Dict, Generator, Tuple, Union, cast

import fastavro as fa
import os
import copy
import json

from typing_extensions import TypedDict

_schema_file = {
    "type": "record",
    "name": "File",
    "fields": [
        {"name": "size", "type": "long"},
        {"name": "hash", "type": "bytes"},
        {"name": "lastModified", "type": "int"},
    ],
}


class CommitManifestFile(TypedDict):
    size: int
    lastModified: float
    hash: bytes


def _is_manifest_file(entity: Any):
    return entity.get("hash") is not None


_schema_directory = {
    "type": "record",
    "name": "Directory",
    "fields": [
        {
            "name": "dirs",
            "type": {"type": "map", "values": "Directory"},
            "default": {},
        },
        {
            "name": "files",
            "type": {"type": "map", "values": _schema_file},
            "default": {},
        },
    ],
}


class CommitManifestDirectory(TypedDict):
    files: Dict[str, CommitManifestFile]
    dirs: Dict[str, "CommitManifestDirectory"]


def _is_manifest_dir(entity: Any):
    has_files = entity.get("files") is not None
    has_dirs = entity.get("dirs") is not None
    return has_files and has_dirs


def _tarverse_record(
    record: CommitManifestDirectory, directory: str = ""
) -> Generator[Tuple[str, CommitManifestFile], None, None]:

    if record is None:
        return

    dirs = record["dirs"]
    for d, nr in dirs.items():
        nd = os.path.join(directory, d)
        for f in _tarverse_record(nr, directory=nd):
            yield f

    files = record["files"]
    for name, file in files.items():
        yield os.path.join(directory, name), file


_schema = {
    "doc": "Manifest containing all files in a single commit",
    "name": "CommitManifest",
    "namespace": "datatorch.artifact.commit.manifest",
    "type": "record",
    "fields": [{"name": "root", "type": _schema_directory}],
}


class CommitManifest:
    @staticmethod
    def schema():
        return _schema

    @classmethod
    def load(cls, file_path: Path) -> "CommitManifest":
        path = file_path.resolve(strict=True)

        if not path.is_file() or not fa.is_avro(str(path)):
            raise ValueError("File must be a AVRO file.")

        with open(str(path), "rb") as manifest_file:
            record = next(fa.reader(manifest_file))
            if record is None:
                raise ValueError("Manifest contains no record.")
            return cls(record)

    def __init__(self, record: dict = None):
        self.record = record if bool(record) else {"root": {"files": {}, "dirs": {}}}

    def __getitem__(
        self, path: str
    ) -> Union[CommitManifestDirectory, CommitManifestFile, None]:
        p = Path(path)
        commit_obj = self.get_dir(p) or self.get_file(p)
        if commit_obj is None:
            raise KeyError(f"Path does not exist.")
        return commit_obj

    def __setitem__(
        self,
        artifact_path: str,
        commit_obj: Union[CommitManifestDirectory, CommitManifestFile],
    ):
        path_artifact = Path(artifact_path)
        path_name = path_artifact.name
        path_parent = path_artifact.parent
        obj_parent = self.get_dir(path_parent)

        if obj_parent is None:
            self._make_dirs(path_artifact)
            obj_parent = self.get_dir(path_parent)

        if _is_manifest_dir(commit_obj):
            obj_parent["dirs"][path_name] = commit_obj  # type: ignore
            return

        if _is_manifest_file(commit_obj):
            obj_parent["files"][path_name] = commit_obj  # type: ignore
            return

        raise ValueError("Invalid commit type.")

    def get_file(self, artifact_path: Path) -> Union[CommitManifestFile, None]:
        parent = artifact_path.parent
        parent_dir = self.get_dir(parent)

        if parent_dir is None:
            return None

        return parent_dir.get("files").get(artifact_path.name)

    def get_dir(self, artifact_path: Path) -> Union[CommitManifestDirectory, None]:
        if str(artifact_path) == ".":
            return self.root_dir

        found_dir = self.root_dir
        for dir in artifact_path.parts:
            found_dir = found_dir["dirs"].get(dir)
            if found_dir is None:
                return None

        return found_dir

    def _make_dirs(self, path: Path):
        if path.parent == ".":
            return self.root_dir

        has_self = self.get_dir(path)
        if has_self:
            return has_self

        has_parent = self.get_dir(path.parent)
        if not has_parent:
            self._make_dirs(path.parent)

        self._insert_dir(path)

    def _insert_dir(self, path: Path, directory: CommitManifestDirectory = None):
        directory = directory or {"files": {}, "dirs": {}}
        dir = self.get_dir(path.parent)
        if dir:
            dir_name = path.name
            dir["dirs"][dir_name] = directory
            return True
        return False

    @property
    def root_dir(self):
        return cast(CommitManifestDirectory, self.record["root"])

    def files(self, directory: CommitManifestDirectory = None):
        record = directory or self.root_dir
        return _tarverse_record(record)

    def write(self, path: Path):
        ps = fa.parse_schema(self.schema())
        with open(path, "wb") as out:
            fa.writer(out, ps, [self.record])
