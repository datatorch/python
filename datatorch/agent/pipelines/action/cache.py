import json
from typing import Any
from datatorch.agent.pipelines.action.config import ActionConfig
from datatorch.utils.hash_table import HashTable


class ActionHashable:
    def __init__(self, id: ActionConfig, inputs: dict):
        self.id = id
        self.inputs = inputs


def action_hash(action: ActionHashable):
    verstion_string = f"{action.id.git}@{action.id.version}"
    inputs_string = json.dumps(action.inputs, sort_keys=True)
    key = f"{verstion_string}+{inputs_string}"
    return key


class ActionHashTable(HashTable[ActionHashable, dict]):
    def __init__(self):
        super().__init__(action_hash)
