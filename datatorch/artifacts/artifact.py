from datatorch.artifacts.commit.commit import Commit, CommitActive
from queue import Queue
from datatorch.utils import exit


class Artifact(object):
    def __init__(self, name: str) -> None:
        self.name = name
        self.to_push: "Queue[CommitActive]" = Queue()
        # self._head = Commit.get(uuid4())
        self._new_commit = CommitActive()
        exit.register(self.push)

    def new_commit(self, branch: str = None):
        return self._new_commit

    def add(self, local_path: str, artifact_path: str = ""):
        self._new_commit.add(local_path, artifact_path=artifact_path)

    def remove(self, artifact_path: str):
        return self._new_commit.remove(artifact_path)

    def get(self, artifact_path: str):
        return self._new_commit.get(artifact_path)

    def commit(self, message: str = "", defer_upload: bool = True):
        self._new_commit.commit(message)
        self.to_push.put(self._new_commit)

    def push(self):
        # self.new_commit.
        print("Uploading")
        for f, _ in self._new_commit.files():
            print(f)
