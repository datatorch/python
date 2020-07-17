import asyncio
from datatorch.utils.files import mkdir_exists
from logging import getLogger

from typing import Union
from ...directory import agent_directory


logger = getLogger(__name__)


class GitCloneBuilder(object):
    def __init__(self, repo: str):
        self.repo = repo
        self._branch = None
        self._path = None
        self._depth = 1

    def branch(self, branch: Union[str, None]):
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
        print(self._branch)
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
            self.version = config.get("tag", "")
            self.git = config.get("git", "")
            self.file = config.get("file", "action-datatorch.yaml")

        if isinstance(config, str):
            name, version = config.strip().split("@", 1)
            self.name = name
            self.version = version
            self.file = "action-datatorch.yaml"
            self.git = ""

        assert self.name != "", "Property 'name' must be provided"
        assert self.version != "", "Property 'version' must be provided"

        # Use `datatorch` as a shortcut to `datatorch-actions`
        if self.name.lower().startswith("datatorch/"):
            self.name = self.name.lower().replace("datatorch/", "datatorch-actions/")

        self.git = self.git or f"git://github.com/{self.name}.git"
        self.depth: int = 1

    async def download(self):
        command = (
            GitCloneBuilder(self.git)
            .depth(1)
            .branch(self.version)
            .path(agent_directory.action_dir(self.name, self.version))
            .build()
        )
        process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL  # type: ignore
        )
        await process.wait()
