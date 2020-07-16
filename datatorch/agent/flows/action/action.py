from datatorch.agent.flows.template import Variables
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


class Action(object):
    def __init__(
        self, action: ActionConfig, directory: str = "./", step: "Step" = None
    ):
        self.dir = directory
        self.identifier = action
        self.config_path = os.path.join(self.dir, action.file)
        self.config = self._load_config()

        self.version = action.version
        self.step = step
        self.name: str = self.config.get("name", action.name)
        self.description: str = self.config.get("description", "")
        self.inputs: dict = self.config.get("inputs", {})
        self.outputs: dict = self.config.get("outputs", {})

        runs = self.config.get("runs")
        if runs is None:
            raise ValueError("Action must have a run section.")

        self.runner = RunnerFactory.create(self, runs)
        self.logger = logging.getLogger(
            "datatorch.agent.action.{}".format(self.identifier)
        )

    def _load_config(self) -> dict:
        with open(self.config_path, "r") as config_file:
            return yaml.load(config_file, Loader=yaml.FullLoader)

    async def run(self, variables: Variables) -> dict:
        logger.info("Running action {}".format(self.identifier))

        variables.set_action(self)
        # Validate input
        for k, v in self.config.get("inputs", {}).items():
            # Set default values
            variable_value = variables.inputs.get(k)

            if variables.inputs.get(k) is None:
                variables.add_input(k, v.get("default"))

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

        if self.step is not None:
            # Update steps output after casting.
            await self.step.update(inputs=variables.inputs)

        logger.debug(f"Inputs for '{self.full_name}': {json.dumps(variables.inputs)}")

        output = (await self.runner.run(variables)) or {}

        logger.info(f"Finished running '{self.full_name}'")
        logger.debug(f"Outputs for '{self.full_name}': {json.dumps(output)}")
        return output

    @property
    def full_name(self) -> str:
        return f"{self.name} v{self.version}"
