import os

from uuid import UUID
from typing import Union

from datatorch.core import folder
from datatorch.utils.files import mkdir_exists


class ArtifactDirectory:
    @staticmethod
    def path() -> str:
        path = folder.get_app_dir()
        return os.getenv("DATATORCH_ARTIFACT_PATH", os.path.join(path, "artifacts"))

    def __init__(self):
        mkdir_exists(self.dir)
        mkdir_exists(self.commits)

    @property
    def dir(self):
        return self.path()

    @property
    def commits(self):
        return os.path.join(self.dir, "commits")

    def commit(self, commit_id: Union[str, UUID]):
        return os.path.join(self.commits, str(commit_id))
