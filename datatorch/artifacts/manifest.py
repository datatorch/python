from pathlib import Path
import atexit
from fastavro import writer


class ArtifactFile(object):
    def __init__(self):
        pass


manifest_schema = {}


class ArtifactManifest(object):
    @classmethod
    def load(cls, path: str):
        return

    @classmethod
    def empty(cls, path: str):
        pass

    def __init__(self):
        atexit.register(
            self.upload,
        )

    def add(self, file: ArtifactFile):
        pass

    def has_file(self, paths):
        pass

    def upload(self, path: str):
        atexit.unregister(self.upload)

    def diff(self, manifest: "ArtifactManifest"):
        pass
