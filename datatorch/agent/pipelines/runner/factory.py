from .runner import Runner
from .command import CommandRunner
from .docker import DockerRunner
from .python import PythonRunner
from .node import NodeRunner
from .shell import ShellRunner

_use_map = {
    "cmd": CommandRunner,
    "commandline": CommandRunner,
    "shell": ShellRunner,
    "script": ShellRunner,
    "docker": DockerRunner,
    "python": PythonRunner,
    "node": NodeRunner,
}


class RunnerCreateError(Exception):
    pass


class RunnerFactory(object):
    @staticmethod
    def create(action, config: dict) -> Runner:
        """Makes runners to 'use' strings found in config.yaml files."""
        use = config.get("using")
        if use is None:
            raise RunnerCreateError("Action 'use' property not specified.")
        if use == "human":
            raise RunnerCreateError(
                "This action is a human task; it cannot be executed by an "
                "agent or in local mode ('datatorch pipeline run'). Run it "
                "through the DataTorch server, which creates a task for a "
                "person to complete."
            )
        if use not in _use_map:
            raise RunnerCreateError("The 'use' type you have entered is invalid.")
        return _use_map[use](config, action)
