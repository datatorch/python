import os
import re
from typing import List, Union
from datatorch.utils.files import mkdir_exists
from datatorch.core import Settings, folder, env, user_settings

# The server refuses a longer action file (MAX_LOCAL_ACTION_TEXT there).
MAX_LOCAL_ACTION_TEXT = 64 * 1024


class RunnerDirectory(object):
    @staticmethod
    def path() -> str:
        """The runner's working directory (actions cache, runs, logs, settings).

        `DATATORCH_RUNNER_PATH` wins, then the pre-rename `DATATORCH_AGENT_PATH`,
        then `<app dir>/runner`. An install that still has `<app dir>/agent`
        from before the rename is moved to `runner` once, so a runner keeps
        its identity, token and cached actions across the upgrade.
        """
        explicit = os.getenv("DATATORCH_RUNNER_PATH") or os.getenv(
            "DATATORCH_AGENT_PATH"
        )
        if explicit:
            return explicit
        app = folder.get_app_dir()
        new = os.path.join(app, "runner")
        old = os.path.join(app, "agent")
        if not os.path.exists(new) and os.path.isdir(old):
            try:
                os.rename(old, new)
            except OSError:
                return old
        return new

    def __init__(self):
        self.settings = RunnerSettings()

        mkdir_exists(self.dir)
        mkdir_exists(self.db_dir)
        mkdir_exists(self.logs_dir)
        mkdir_exists(self.temp_dir)
        mkdir_exists(self.runs_dir)
        mkdir_exists(self.actions_dir)
        mkdir_exists(self.projects_dir)

    @property
    def root(self):
        return self.path()

    @property
    def dir(self):
        return self.path()

    @property
    def runs_dir(self):
        return os.path.join(self.dir, "runs")

    @property
    def logs_dir(self):
        """Directory where agent logs are stored."""
        return os.path.join(self.dir, "logs")

    @property
    def db_dir(self):
        """Sqlite database are stored."""
        return os.path.join(self.dir, "db")

    @property
    def projects_dir(self):
        """Directory where projects are stored.

        Commonly used for caching project information such as annotations and
        files.
        """
        return os.path.join(self.dir, "projects")

    @property
    def actions_dir(self):
        """Directory where actions are stored."""
        return os.path.join(self.dir, "actions")

    def open(self, file: str, mode: str):
        return open(os.path.join(self.dir, file), mode)

    def action_dir(self, name: str, version: str):
        return os.path.join(self.actions_dir, *name.lower().split("/"), version)

    # Folder name and tag the server accepts for a local action
    # (services/api/src/modules/runners/localActions.ts).
    LOCAL_ACTION_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
    LOCAL_ACTION_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
    ACTION_FILES = (
        "action-datatorch.yaml",
        "action-datatorch.yml",
        "action-datatorch.json",
    )

    @property
    def local_actions_dir(self):
        """Where a person keeps their own actions: `actions/local/<name>/<tag>`.

        A pipeline step references one as `local/<name>@<tag>`; the folder
        is run as-is and never fetched from anywhere.
        """
        return os.path.join(self.actions_dir, "local")

    def local_actions(self) -> List[dict]:
        """Every `actions/local/<name>/<tag>` folder holding an action file,
        as `{name, tag, text}` with the action file's text, sorted. This is
        what the runner reports to the server so the pipeline editor can list
        and wire the action: the yaml only, never the code."""
        found = []
        root = self.local_actions_dir
        if not os.path.isdir(root):
            return found
        for name in sorted(os.listdir(root)):
            name_dir = os.path.join(root, name)
            if not os.path.isdir(name_dir) or not self.LOCAL_ACTION_NAME.match(name):
                continue
            for tag in sorted(os.listdir(name_dir)):
                tag_dir = os.path.join(name_dir, tag)
                if not os.path.isdir(tag_dir) or not self.LOCAL_ACTION_TAG.match(tag):
                    continue
                for file in self.ACTION_FILES:
                    path = os.path.join(tag_dir, file)
                    if not os.path.isfile(path):
                        continue
                    try:
                        with open(path, "r", encoding="utf-8") as handle:
                            text = handle.read(MAX_LOCAL_ACTION_TEXT + 1)
                    except OSError:
                        continue
                    # A .json file is read by the server's yaml parser as-is.
                    found.append({"name": name, "tag": tag, "text": text})
                    break
        return found

    # What the editor reads from and writes into a folder (the server caps
    # the same way; this side is the one that matters).
    MAX_LOCAL_ACTION_FILES = 40
    MAX_LOCAL_ACTION_FILE_TEXT = 256 * 1024
    SKIPPED_DIRS = ("__pycache__", "node_modules", ".git", "venv", ".venv")

    def local_action_dir(self, name: str, tag: str) -> str:
        """`actions/local/<name>/<tag>`, for a name and tag that are folder
        names (anything else is refused, never joined)."""
        if not self.LOCAL_ACTION_NAME.match(name or ""):
            raise ValueError(f"'{name}' is not a local action folder name.")
        if not self.LOCAL_ACTION_TAG.match(tag or ""):
            raise ValueError(f"'{tag}' is not a tag folder name.")
        return os.path.join(self.local_actions_dir, name, tag)

    def _inside(self, folder: str, rel: str) -> str:
        """The absolute path of `rel` inside `folder`, or a ValueError: no
        absolute paths, no `..`, no hidden segments, no symlink escapes."""
        rel = (rel or "").replace("\\", "/").strip()
        if not rel or rel.startswith("/"):
            raise ValueError(f"'{rel}': use a relative path.")
        for part in rel.split("/"):
            if part in ("", ".", "..") or part.startswith("."):
                raise ValueError(f"'{rel}': not a path inside the action folder.")
        root = os.path.realpath(folder)
        full = os.path.realpath(os.path.join(root, *rel.split("/")))
        if full != root and not full.startswith(root + os.sep):
            raise ValueError(f"'{rel}': not a path inside the action folder.")
        return full

    def local_action_files(self, name: str, tag: str) -> List[dict]:
        """The text files of one local action folder, as `{path, text, size}`,
        sorted; binaries, hidden files, caches and big files are left out."""
        folder = self.local_action_dir(name, tag)
        if not os.path.isdir(folder):
            raise FileNotFoundError(
                f"No folder actions/local/{name}/{tag} on this runner."
            )
        found = []
        for root, dirs, files in os.walk(folder):
            dirs[:] = sorted(
                d for d in dirs if not d.startswith(".") and d not in self.SKIPPED_DIRS
            )
            for file in sorted(files):
                if file.startswith("."):
                    continue
                full = os.path.join(root, file)
                if os.path.islink(full):
                    continue
                size = os.path.getsize(full)
                if size > self.MAX_LOCAL_ACTION_FILE_TEXT:
                    continue
                try:
                    with open(full, "r", encoding="utf-8") as handle:
                        text = handle.read()
                except (OSError, UnicodeDecodeError):
                    continue
                rel = os.path.relpath(full, folder).replace(os.sep, "/")
                found.append({"path": rel, "text": text, "size": size})
                if len(found) >= self.MAX_LOCAL_ACTION_FILES:
                    return found
        return found

    def write_local_action_files(
        self, name: str, tag: str, files: List[dict], delete: List[str] = None
    ) -> List[dict]:
        """Writes `files` (`{path, text}`) into, and deletes `delete` from, one
        local action folder, creating the folder when it is new. Every path
        is checked to be inside the folder before anything is touched."""
        folder = self.local_action_dir(name, tag)
        writes = [
            (self._inside(folder, f.get("path")), f.get("text") or "")
            for f in files or []
        ]
        removes = [self._inside(folder, p) for p in delete or []]
        for _, text in writes:
            if len(text) > self.MAX_LOCAL_ACTION_FILE_TEXT:
                raise ValueError("A file is longer than the editor allows.")
        mkdir_exists(folder)
        for full, text in writes:
            mkdir_exists(os.path.dirname(full))
            with open(full, "w", encoding="utf-8") as handle:
                handle.write(text)
        for full in removes:
            if os.path.isfile(full):
                os.remove(full)
        return self.local_action_files(name, tag)

    def run_dir(self, task_id: str):
        """Returns the directory for a given task"""
        path = os.path.join(self.runs_dir, task_id)
        mkdir_exists(path)
        return path

    def project_dir(self, project_id: str):
        """Returns the directory for a given project"""
        path = os.path.join(self.projects_dir, project_id)
        mkdir_exists(path)
        return path

    @property
    def temp_dir(self):
        return os.path.join(self.dir, "temp")


class RunnerSettings(Settings):
    """The runner's own settings file. Keys are `runnerId` / `runnerToken`;
    the pre-rename `agentId` / `agentToken` are still read, so an upgraded
    runner keeps working until it is re-registered."""

    def __init__(self):
        super().__init__(RunnerDirectory.path())

    @property
    def runner_id(self):
        return (
            os.getenv(env.RUNNER_ID)
            or self.get("runnerId", env=env.AGENT_ID)
            or self.get("agentId")
        )

    @runner_id.setter
    def runner_id(self, value):
        self.set("runnerId", value)

    @property
    def runner_token(self):
        return self.get("runnerToken") or self.get("agentToken")

    @runner_token.setter
    def runner_token(self, value):
        self.set("runnerToken", value)

    # Pre-rename names, kept for callers outside this package.
    agent_id = runner_id
    agent_token = runner_token

    @property
    def api_url(self):
        return self.get("apiUrl", user_settings.api_url)

    @api_url.setter
    def api_url(self, value):
        self.set("apiUrl", value)


runner_directory = RunnerDirectory()

# Pre-rename names, kept for callers outside this package.
AgentDirectory = RunnerDirectory
AgentSettings = RunnerSettings
agent_directory = runner_directory
