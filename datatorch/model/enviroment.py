from enum import Enum
from pathlib import Path


class PythonEnvironmentType(Enum):
    Pip = "pip"
    PipTools = "pip-tools"
    Pipenv = "pipenv"
    Conda = "conda"

    @classmethod
    def getenvconfig():
        pass


class PythonEnvironment:
    @classmethod
    def load(cls, path: str):
        config_path = Path(path)
        is_file = config_path.is_file()

    def __init__(self):
        self.type: PythonEnvironmentType = PythonEnvironmentType.Conda

    def install(self):
        pass
