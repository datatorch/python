from datatorch.agent.pipelines.action.cache import ActionHashable, ActionHashTable
from datatorch.agent.pipelines.template import Variables
from datatorch.utils.objects import pick

from typing import Any, Dict, Union
import os
import yaml
import logging
import json
import typing

from .config import ActionConfig
from ..runner import RunnerFactory

if typing.TYPE_CHECKING:
    from ..step import Step


logger = logging.getLogger("datatorch.agent.action")

_actions_cache = ActionHashTable()


class Action(object):
    def __init__(
        self,
        config: ActionConfig,
        directory: str = "./",
        step: "Union[Step, None]" = None,
    ):
        self.dir = directory
        self.identifier = config
        self.config_path = os.path.join(self.dir, config.file)
        self.config = self._load_config()
        self.cacheable = self.config.get("cache", False)

        self.version = config.version
        self.step = step
        self.name: str = self.config.get("name", config.name)
        self.description: str = self.config.get("description", "")
        self.inputs: dict = self.config.get("inputs", {})
        self.outputs: dict = self.config.get("outputs", {})
        self.cache = _actions_cache

        runs = self.config.get("runs")
        if runs is None:
            raise ValueError("Action must have a run section.")

        self.runner = RunnerFactory.create(self, runs)

    def _load_config(self) -> dict:
        with open(self.config_path, "r") as config_file:
            return yaml.load(config_file, Loader=yaml.FullLoader)

    def cache_enabled(self):
        """Determine if this action should be cached.

        The pipeline has the file say. If cache is enabled or display in the
        pipeline it will be disabled here. If its not specified it will be up to
        the action.
        """
        if self.step:
            if self.step.cacheable is not None:
                return self.step.cacheable
        return self.cacheable

    def get_cached(self, variables: Variables):
        if self.cache_enabled():
            inputs = pick(variables.inputs.copy(), list(self.inputs.keys()))
            hash_obj = ActionHashable(self.identifier, inputs)
            return self.cache.get(hash_obj)
        return None

    def set_cache(self, variables: Variables, value):
        if self.cache_enabled():
            inputs = pick(variables.inputs.copy(), list(self.inputs.keys()))
            hash_obj = ActionHashable(self.identifier, inputs)
            self.cache.set(hash_obj, value)

    async def run(self, variables: Variables) -> Dict[str, Any]:
        logger.info("Running {}".format(self.identifier.full_name))

        variables.set_action(self)
        # Validate input
        for k, v in self.config.get("inputs", {}).items():
            # Set default values
            if variables.inputs.get(k) is None:
                variables.add_input(k, v.get("default"))

            variable_value = variables.inputs.get(k)

            if variable_value is None:
                # Error if input is required but missing
                if v.get("required", False):
                    raise ValueError(f"Value required for input '{k}'")
            else:
                # Check value typing
                variable_type = v.get("type")

                if not variable_type:
                    continue

                if variable_type == "float":
                    variables.add_input(k, float(variable_value))

                if variable_type == "integer":
                    variables.add_input(k, int(variable_value))

                if variable_type == "string":
                    variables.add_input(k, str(variable_value))

                if variable_type == "boolean":
                    variables.add_input(k, bool(variable_value))

                if variable_type == "array" or variable_type == "list":
                    if isinstance(variable_value, str):
                        variable_value = json.loads(variable_value)
                    variables.add_input(k, variable_value)

        if self.step is not None:
            # Update steps output after casting.
            await self.step.update(inputs=variables.inputs)

        logger.debug(f"Inputs for '{self.full_name}': {json.dumps(variables.inputs)}")

        output = self.get_cached(variables)

        if output is None:
            output = (await self.runner.run(variables)) or {}
            self.set_cache(variables, output)
        else:
            logger.info("Results found in cache.")
            if self.step:
                self.step.log("Results found in cache.")

        logger.info(f"Finished running '{self.full_name}'")
        logger.debug(f"Outputs for '{self.full_name}': {json.dumps(output)}")
        return output

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.version}"
