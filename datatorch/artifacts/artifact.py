from pathlib import Path

import os


class Commit(object):
    def __init__(self):
        pass

    def add_modal(self, local_path: str, artifact_path: str = None):
        pass

    def add_file(self, local_path: str, artifact_path: str = None):
        path = Path(local_path).resolve(strict=True)
        if not path.is_file():
            raise ValueError(f"Path is not a file. '{local_path}' must be a file.")
        print(path.lstat())

    def add_dir(self, local_path: str, pattern: str = "*", artifact_path: str = ""):
        path = Path(local_path).resolve(strict=True)
        if not path.is_dir():
            raise ValueError(f"Local path: '{local_path}' must be a directory.")
        for file in path.rglob(pattern):
            ap = os.path.join(artifact_path, file.relative_to(path))
            self.add_file(str(file), artifact_path=ap)


class Artifact(object):
    def __init__(self) -> None:
        self.new_commit: Commit = Commit()

    def add_modal(self, local_path: str, artifact_path: str = None):
        return self.new_commit.add_modal(local_path, artifact_path=artifact_path)

    def add_file(self, local_path: str, artifact_path: str = None):
        return self.new_commit.add_file(
            local_path=local_path, artifact_path=artifact_path
        )

    def add_dir(self, local_path: str, pattern: str = "*", artifact_path: str = ""):
        return self.new_commit.add_dir(
            local_path, pattern=pattern, artifact_path=artifact_path
        )

    def commit(self):

        self.new_commit = Commit()
