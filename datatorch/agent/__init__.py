"""Deprecated: the runner package moved to `datatorch.runner` (October 2026).

`datatorch.agent` keeps exporting the package's public names for existing
scripts; submodule imports (`datatorch.agent.pipelines`) must switch to
`datatorch.runner.pipelines`.
"""

import warnings

from datatorch.runner import *  # noqa: F401,F403
from datatorch.runner import RunnerDaemon as Agent  # noqa: F401
from datatorch.runner import __all__  # noqa: F401
from datatorch.runner.directory import (  # noqa: F401
    RunnerDirectory as AgentDirectory,
    RunnerSettings as AgentSettings,
    runner_directory as agent_directory,
)

warnings.warn(
    "datatorch.agent is deprecated; import datatorch.runner instead.",
    DeprecationWarning,
    stacklevel=2,
)
