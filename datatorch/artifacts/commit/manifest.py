from typing import Any, Dict, Generator, Tuple, Union, cast
from typing_extensions import TypedDict

from pathlib import Path
import fastavro as fa
import os


_schema_file = {
    "type": "record",
    "name": "File",
    "fields": [
        {"name": "size", "type": "long"},
        {"name": "hash", "type": "bytes"},
        {"name": "lastModified", "type": "float"},
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
    "doc": "Manifest containing all files for a single commit",
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

    def get_file(self, artifact_path: Path) -> Union[CommitManifestFile, None]:
        parent = artifact_path.parent
        parent_dir = self.get_dir(
            parent,
        )
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

    def get(self, artifact_path: Path):
        return self.get_file(artifact_path) or self.get_dir(artifact_path)

    def add(
        self,
        artifact_path: Path,
        commit_obj: Union[CommitManifestDirectory, CommitManifestFile],
    ):
        path_name = artifact_path.name
        path_parent = artifact_path.parent
        obj_parent = self._make_dirs(path_parent)

        if obj_parent is None:
            raise ValueError(
                "Failed to insert files into manifest. Parent object not found."
            )

        if _is_manifest_dir(commit_obj):
            obj_parent["dirs"][path_name] = commit_obj  # type: ignore
            return True

        if _is_manifest_file(commit_obj):
            obj_parent["files"][path_name] = commit_obj  # type: ignore
            return True

        raise ValueError("Invalid commit type.")

    def remove(self, artifact_path: Path):
        parent_path = artifact_path.parent
        parent = self.get_dir(parent_path)

        if parent:
            parent["files"].pop(artifact_path.name)
            parent["dirs"].pop(artifact_path.name)

    def _make_dirs(self, path: Path):
        if path.parent == ".":
            return self.root_dir

        has_self = self.get_dir(path)
        if has_self:
            return has_self

        has_parent = self.get_dir(path.parent)
        if not has_parent:
            # make parent directory first
            self._make_dirs(path.parent)

        # create directory
        created_dir: CommitManifestDirectory = {"files": {}, "dirs": {}}
        self.add(path, created_dir)

        return created_dir

    @property
    def root_dir(self):
        return cast(CommitManifestDirectory, self.record["root"])

    def files(self, directory: CommitManifestDirectory = None):
        record = directory or self.root_dir
        return _tarverse_record(record)

    def diff(self, manifest: "CommitManifest" = None):

        current_files = set(map(lambda p: p[1]["hash"], self.files()))
        other_files = set(
            map(lambda p: p[1]["hash"], (manifest and manifest.files()) or [])
        )

        created = current_files.difference(other_files)
        deleted = other_files.difference(current_files)

        return created, deleted

    def write(self, path: Path):
        ps = fa.parse_schema(self.schema())
        with open(path, "wb") as out:
            fa.writer(out, ps, [self.record])
