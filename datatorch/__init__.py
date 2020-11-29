import sys
import json
from typing import Any

from datatorch.api import ApiClient
from datatorch.artifacts import Artifact, Commit
from datatorch.core import BASE_URL, BASE_URL_API

__all__ = [
    # Api
    "BASE_URL",
    "BASE_URL_API",
    "ApiClient",
    # Agent
    "get_inputs",
    # Artifact
    "Artifact",
    "Commit",
    "CommitActive",
]


_inputs = None


def get_inputs() -> dict:
    global _inputs
    try:
        if _inputs is None:
            _inputs = json.loads(sys.argv[-1])
        return _inputs
    except:
        return {}


def get_input(key: str) -> Any:
    return get_inputs().get(key)


def set_output(var: str, value: Any):
    print(f"::{var}::{json.dumps(value)}")
