import asyncio, os, shutil
from datatorch import agent
from datatorch.utils.files import mkdir_exists
from logging import getLogger

from typing import Union
from ...directory import agent_directory


logger = getLogger(__name__)


LATEST_VERSION = "latest"


class GitCloneBuilder(object):
    def __init__(self, repo: str):
        self.repo = repo
        self._branch = None
        self._path = None
        self._depth = 1

    def branch(self, branch: Union[str, None]):
        if branch != LATEST_VERSION:
            self._branch = branch
        return self

    def depth(self, depth: int):
        self._depth = depth
        return self

    def path(self, path: Union[str, None]):
        self._path = path
        return self

    def build(self):
        base = f"git clone --depth {self._depth} --single-branch -q "
        if self._branch:
            base += f"--branch {self._branch} "
        base += f"{self.repo} "
        if self._path:
            base += f"{self._path} "
        return base


class ActionConfig(object):
    def __init__(self, config: Union[dict, str]):
        if isinstance(config, dict):
            self.name = config.get("name", "")
            self.version = config.get("tag", LATEST_VERSION)
            self.git = config.get("git", "")
            self.file = config.get("file", "action-datatorch.yaml")

        if isinstance(config, str):
            name, version = config.strip().split("@", 1)
            self.name = name
            self.version = version or LATEST_VERSION
            self.file = "action-datatorch.yaml"
            self.git = ""

        assert self.name != "", "Property 'name' must be provided"

        # Use `datatorch` as a shortcut to `datatorch-actions`
        if self.name.lower().startswith("datatorch/"):
            self.name = self.name.lower().replace("datatorch/", "datatorch-actions/")

        self.git = self.git or f"git://github.com/{self.name}.git"
        self.depth: int = 1

    async def download(self):
        path = agent_directory.action_dir(self.name, self.version)
        if os.path.isdir(path):
            shutil.rmtree(path)

        command = (
            GitCloneBuilder(self.git).depth(1).branch(self.version).path(path).build()
        )
        process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL  # type: ignore
        )
        await process.wait()

    @property
    def full_name(self):
        return f"{self.name}@{self.version}"
