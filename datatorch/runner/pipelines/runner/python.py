import os
import sys
import json
import shlex
import hashlib

from .runner import Runner
from datatorch.runner.directory import runner_directory


class PythonFailedError(Exception):
    pass


REQUIREMENTS_FILE = "requirements.txt"
STAMP_FILE = ".requirements.sha256"


class PythonRunner(Runner):
    """Runs `main` with Python.

    An action that ships a `requirements.txt` (October 2026) runs in its
    own environment, built on first use under the runner's `envs/`
    folder and rebuilt when the requirements change. The environment
    sees the runner's own packages too (`--system-site-packages`), so the
    DataTorch SDK and what the runner already has need not be listed.
    Without a requirements file, the runner's interpreter is used as
    before.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.config.get("main") is None:
            raise ValueError("A main path was not provided.")

    def requirements_path(self) -> str:
        return os.path.join(self.action.dir, REQUIREMENTS_FILE)

    def env_dir(self) -> str:
        identifier = self.action.identifier
        parts = [p for p in str(identifier.name).lower().split("/") if p]
        return os.path.join(runner_directory.envs_dir, *parts, str(identifier.version))

    @staticmethod
    def env_python(env_dir: str) -> str:
        if os.name == "nt":
            return os.path.join(env_dir, "Scripts", "python.exe")
        return os.path.join(env_dir, "bin", "python")

    async def ensure_environment(self) -> str:
        """The interpreter to run `main` with: the action's own when it has
        requirements (installing them when missing or changed), else ours."""
        requirements = self.requirements_path()
        if not os.path.isfile(requirements):
            return sys.executable
        with open(requirements, "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
        env_dir = self.env_dir()
        python = self.env_python(env_dir)
        stamp = os.path.join(env_dir, STAMP_FILE)
        current = None
        if os.path.isfile(stamp):
            with open(stamp, "r") as handle:
                current = handle.read().strip()
        if os.path.isfile(python) and current == digest:
            return python

        self.log(f"Preparing the action's Python environment in {env_dir}")
        os.makedirs(os.path.dirname(env_dir), exist_ok=True)
        if not os.path.isfile(python):
            await self.monitor_cmd(
                " ".join(
                    shlex.quote(part)
                    for part in (
                        sys.executable,
                        "-m",
                        "venv",
                        "--system-site-packages",
                        env_dir,
                    )
                )
            )
        self.log(f"Installing {REQUIREMENTS_FILE} (first run, or the file changed)")
        await self.monitor_cmd(
            " ".join(
                shlex.quote(part)
                for part in (
                    python,
                    "-m",
                    "pip",
                    "install",
                    "--quiet",
                    "-r",
                    requirements,
                )
            )
        )
        with open(stamp, "w") as handle:
            handle.write(digest)
        return python

    async def execute(self):
        main = self.get("main").strip("/")
        main_path = os.path.join(self.action.dir, main)
        python = await self.ensure_environment()

        # Inputs reach the action verbatim as one JSON argv argument.
        # shlex.quote covers every shell metacharacter, apostrophes
        # included, and the space in macOS "Application Support" paths.
        json_input = json.dumps(self.variables.inputs)

        await self.monitor_cmd(
            " ".join(shlex.quote(part) for part in (python, main_path, json_input))
        )
