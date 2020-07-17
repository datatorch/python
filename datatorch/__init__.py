import sys
import json
from typing import Any
from datatorch.api import ApiClient


__all__ = ["ApiClient", "get_inputs"]


def get_inputs(key: str = None) -> dict:
    try:
        values = json.loads(sys.argv[-1])
        return values.get(key) if key else values
    except Exception as e:
        return {}


def set_output(var: str, value: Any):
    print(f"::{var}::{json.dumps(value)}")
