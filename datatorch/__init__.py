import sys
import json
from typing import Any
from datatorch.api import ApiClient


__all__ = ["ApiClient", "get_inputs"]


_inputs = None


def get_inputs(key: str = None) -> dict:
    global _inputs
    try:
        if _inputs is None:
            _inputs = json.loads(sys.argv[-1])
        return _inputs.get(key) if key else _inputs
    except:
        return {}


def set_output(var: str, value: Any):
    print(f"::{var}::{json.dumps(value)}")
