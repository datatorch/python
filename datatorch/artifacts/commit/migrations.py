from uuid import UUID
from io import BufferedWriter
from pathlib import Path
from typing import Dict, Set, Tuple, Union

from datetime import datetime
import fastavro as fa


_schema_action = {
    "type": "enum",
    "name": "CommitMigrationAction",
    "symbols": ["CREATED", "DELETED"],
}

_schema_map = {"type": "map", "values": _schema_action}

_schema = {
    "doc": "Commit migrations contains all changes made for a single commit",
    "name": "CommitMigrations",
    "namespace": "datatorch.artifact.commit.migrations",
    "type": "record",
    "fields": [
        {"name": "commitId", "type": "bytes"},
        {"name": "fromCommitId", "type": ["bytes", "null"]},
        {"name": "createdAt", "type": "int"},
        {
            "name": "migrations",
            "type": _schema_map,
            "default": {},
        },
    ],
}


class CommitMigrations:
    @classmethod
    def load(cls, migrations_file: Path) -> "CommitMigrations":
        path = migrations_file.resolve(strict=True)

        if not path.is_file() or not fa.is_avro(str(path)):
            raise ValueError("File must be a AVRO file.")

        with open(path, "rb") as fp:
            record = next(fa.reader(fp), None)
            if record is None:
                raise ValueError("Migrations contains no record.")

            # Get values
            commit_id: bytes = record["commitId"]
            from_commit_id: Union[bytes, None] = record["fromCommitId"]
            migrations: Dict[str, str] = record["migrations"]

            # Convert to correct format
            from_commit_uuid = UUID(bytes=from_commit_id) if from_commit_id else None

            return cls(
                UUID(bytes=commit_id), migrations, from_commit_id=from_commit_uuid
            )

    @staticmethod
    def schema():
        return _schema

    def __init__(
        self,
        commit_id: UUID,
        migrations: Dict[str, str],
        from_commit_id: UUID = None,
    ):
        self.commit_id = commit_id
        self.from_commit_id = from_commit_id
        self.migrations = migrations

    def writer(self, buffer: BufferedWriter):
        ps = fa.parse_schema(self.schema())

        fa.writer(
            buffer,
            ps,
            [
                {
                    "commitId": self.commit_id.bytes,
                    "fromCommitId": self.from_commit_id and self.from_commit_id.bytes,
                    "createdAt": datetime.utcnow().timestamp(),
                    "migrations": self.migrations,
                }
            ],
        )

    def write(self, buff: Union[str, Path]):
        with open(buff, "wb") as out:
            self.writer(out)

    def to_sets(self) -> Tuple[Set[str], Set[str]]:
        created = set([])
        deleted = set([])
        for k, v in self.migrations.items():
            if v == "CREATED":
                created.add(k)
            if v == "DELETED":
                deleted.add(k)
        return created, deleted
