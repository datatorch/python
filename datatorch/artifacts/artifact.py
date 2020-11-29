from datatorch.artifacts.commit.commit import CommitActive
from queue import Queue
from datatorch.core import user_settings


class Artifact(object):
    def __init__(self, name: str) -> None:
        self.name = name
        self._new_commits: "Queue[CommitActive]" = Queue()
        # self._head = Commit.get(uuid4())
        self._new_commit = CommitActive()

    def new_commit(self, branch: str = None):
        return self._new_commit

    def add(self, local_path: str, artifact_path: str = ""):
        self._new_commit.add(local_path, artifact_path=artifact_path)

    def remove(self, artifact_path: str):
        return self._new_commit.remove(artifact_path)

    def get(self, artifact_path: str):
        return self._new_commit.get(artifact_path)

    def commit(self, message: str = ""):
        # Create Commit
        # Queue Items to upload
        # Create new commit
        c = self._new_commit
        c.commit()
        cm = c.migrations()
        cm.migrations

        for hash, action in cm.migrations.items():
            if action == "CREATED":
                url = f"{user_settings.api_url}/file/v2/commit/{self._new_commit.commit_id}/files/{hash}"
                print(url)
