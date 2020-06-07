import logging
import json
import os

from datatorch.core import folder

logger = logging.getLogger(__name__)

SETTINGS_FILE = "settings.json"


class Settings(object):
    """ Manager for storaging user settings such as API KEY and API URL """

    def __init__(self):
        # self.local_path = os.path.join(folder.local_path(), SETTINGS_FILE)
        self.global_path = os.path.join(folder.global_path(), SETTINGS_FILE)

        # self._local = load_json(self.local_path)
        self._local = dict({})
        self._global = load_json(self.global_path)

    def get(self, key: str, default=None):
        env_value = os.getenv("DATATORCH_{}".format(key.upper()))
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
            # self._local[key] = value
            # save_json(self.local_path, self._local)
            pass


def load_json(path: str) -> dict:

    with open(path) as fr:
        output = fr.read()
        data = json.loads(output or "{}")

    return data


def save_json(path: str, settings: dict):
    with open(path, "w") as f:
        json.dump(settings, f, indent=2, sort_keys=True)
