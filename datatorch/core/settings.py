from typing import Union

import logging
import json
import os

from datatorch.utils.url import normalize_api_url
from datatorch.utils.files import mkdir_exists
from datatorch.core import folder, env

logger = logging.getLogger(__name__)


class Settings(object):
    """ Manager for storing settings in a JSON file. """

    def __init__(self, path: str, file_name="settings.json"):
        self.path = path
        mkdir_exists(path)
        self.file = os.path.join(path, file_name)
        self.settings = _load_json(self.file)

    def get(self, key: str, default=None, env: str = None) -> str:
        """ Gets the settings value from a given string. """
        env_value = os.getenv(f"DATATORCH_{env}") if env is not None else None
        value = self.settings.get(key)

        return env_value or value or default

    def set(self, key: str, value: Union[str, None]) -> None:
        """ Saves a value to the settings file. """
        self.settings[key] = value
        _save_json(self.file, self.settings)


class UserSettings(Settings):
    def __init__(self):
        super().__init__(folder.get_app_dir(), "settings.json")

    @property
    def api_key(self):
        return self.get("apiKey", env=env.API_KEY)

    @api_key.setter
    def api_key(self, value: Union[str, None]):
        self.set("apiKey", value if value is None else value.strip())

    @property
    def api_url(self):
        return self.get("apiUrl", env=env.API_URL)

    @api_url.setter
    def api_url(self, value: Union[str, None]):
        self.set("apiUrl", value if value is None else normalize_api_url(value))


def _load_json(path: str) -> dict:

    try:
        with open(path) as fr:
            output = fr.read()
            data = json.loads(output or "{}")
        return data
    except FileNotFoundError:
        pass

    return {}


def _save_json(path: str, settings: dict):
    with open(path, "w") as f:
        json.dump(settings, f, indent=2, sort_keys=True)
