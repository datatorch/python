from enum import Enum

import json
import os

from datatorch.core import env, folder


SETTINGS_FILE = 'settings.json'


class Setting(Enum):
    API_KEY = 'API_KEY'
    HOST_URL = 'HOST_URL'


class Settings(object):

    def __init__(self, local: bool = True):
        self.local_path = os.path.join(folder.local_path(), SETTINGS_FILE)
        self.global_path = os.path.join(folder.global_path(), SETTINGS_FILE)

        self._local = load_json(self.local_path)
        self._global = load_json(self.global_path)

    def get(self, key: Setting, default=None):
        key = key.value
        env_value = os.getenv('DATATORCH_{}'.format(key.upper()))
        local_value = self._local.get(key)
        global_value = self._global.get(key)

        return env_value or local_value or global_value or default

    def set(self, key: str, value: str, globally=False, persist=True):
        os.environ[key] = value

        if not persist:
            return

        if globally:
            self._global[key] = value
            save_json(self.global_path, self._global)
        else:
            self._local[key] = value
            save_json(self.local_path, self._local)


def load_json(path: str) -> dict:

    with open(path) as fr:
        output = fr.read()
        data = json.loads(output or '{}')

    return data


def save_json(path: str, settings: dict):
    with open(path, 'w') as f:
        json.dump(settings, f, indent=2, sort_keys=True)
