from datatorch.artifacts.directory import ArtifactDirectory
from io import BufferedWriter
from typing import Any, Dict, Generator, Set, Tuple, Union, cast
from uuid import UUID
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
    "fields": [
        {"name": "commitId", "type": "bytes"},
        {"name": "previousCommitId", "type": ["bytes", "null"]},
        {"name": "branch", "type": "string", "default": "main"},
        {"name": "root", "type": _schema_directory},
    ],
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
            record = next(fa.reader(manifest_file), None)
            if record is None:
                raise ValueError("Manifest does not contain any records.")

            commit_id: bytes = record["commitId"]
            root: CommitManifestDirectory = record["root"]
            commit_previous_id: Union[bytes, None] = record["previousCommitId"]
            commit_previous_uuid = (
                UUID(bytes=commit_previous_id) if commit_previous_id else None
            )

            return cls(
                UUID(bytes=commit_id),
                root=root,
                previous_commit_id=commit_previous_uuid,
            )

    def __init__(
        self,
        commit_id: UUID,
        root: CommitManifestDirectory = None,
        previous_commit_id: UUID = None,
    ):
        self.commit_id = commit_id
        self.previous_commit_id: Union[None, UUID] = previous_commit_id
        self.root = root or cast(CommitManifestDirectory, {"files": {}, "dirs": {}})

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
            return self.root

        found_dir = self.root
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
            return self.root

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

    def files(self, directory: CommitManifestDirectory = None):
        record = directory or self.root
        return _tarverse_record(record)

    def diff(self, manifest: "CommitManifest" = None):
        current_files: Set[str] = set(map(lambda p: p[1]["hash"].hex(), self.files()))
        other_files: Set[str] = set(
            map(lambda p: p[1]["hash"].hex(), (manifest and manifest.files()) or [])
        )

        created = current_files.difference(other_files)
        deleted = other_files.difference(current_files)

        return created, deleted

    def writer(self, buffer: BufferedWriter):
        ps = fa.parse_schema(self.schema())
        record = dict(
            commitId=self.commit_id.bytes,
            root=self.root,
            previousCommitId=self.previous_commit_id and self.previous_commit_id.bytes,
        )
        fa.writer(buffer, ps, [record])

    def write(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as out:
            self.writer(out)
