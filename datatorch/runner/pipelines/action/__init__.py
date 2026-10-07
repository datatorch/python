from .action import Action

import os
import logging
import typing

from datatorch.runner.directory import runner_directory
from .config import ActionConfig, LATEST_VERSION

if typing.TYPE_CHECKING:
    from ..step import Step


__all__ = ["Action", "get_action"]


logger = logging.getLogger("datatorch.runner.action")


async def get_action(config: ActionConfig, step: "Step" = None) -> Action:
    # Get actions directory
    action_dir = runner_directory.action_dir(config.name, config.version)
    folder_exists = os.path.exists(action_dir)
    force_download = config.version == LATEST_VERSION

    if folder_exists and not force_download:
        logger.debug(
            "Action found locally ({}@{}).".format(config.name, config.version)
        )
    else:
        logger.debug("Downloading action {}@{}.".format(config.name, config.version))
        await config.download()

    return Action(config, action_dir, step=step)
