from .action import Action

import os
import logging

from datatorch.api import ApiClient
from datatorch.agent.directory import agent_directory


__all__ = ["Action", "get_action"]


logger = logging.getLogger("datatorch.agent.action")


def _download_action(api: ApiClient, name, version):
    pass


def get_action(action: str, agent=None) -> Action:
    name, version = action.split("@", 1)

    # Get actions directory
    action_dir = agent_directory.action_dir(name, version)
    folder_exists = os.path.exists(action_dir)

    if folder_exists:
        logger.debug("Action found locally ({}@{}).".format(name, version))
    else:
        logger.debug("Downloading action {}@{}.".format(name, version))

    return Action(action, action_dir, agent=agent)
