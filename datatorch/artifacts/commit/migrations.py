from enum import Enum


class CommitMigrationAction(Enum):
    Deleted = 0
    Created = 1


class CommitFileMigration:
    """
    A single action that happened to a file.
    Only of these can occur per commit.
    """

    def __init__(self, commit: str, action: CommitMigrationAction):
        self.commit = commit
        self.action = action


class CommitMigration:
    def __init__(self, file_hash: bytes, action: CommitMigrationAction):
        self.action = action
        self.file_hash = file_hash
