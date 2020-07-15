import os
import yaml
import logging
import json
import typing

from ..runner import RunnerFactory

if typing.TYPE_CHECKING:
    from ..step import Step


logger = logging.getLogger("datatorch.agent.action")


class Action(object):
    def __init__(
        self, action: str = "default@1", directory: str = "./", step: "Step" = None
    ):
        name, version = action.split("@", 1)

        self.dir = directory
        self.identifier = action
        self.config_path = os.path.join(self.dir, "action-datatorch.yaml")
        self.config = self._load_config()

        self.version = version
        self.step = step
        self.name: str = self.config.get("name", name)
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

    async def run(self, inputs: dict = {}) -> dict:
        logger.info("Running action {}".format(self.identifier))

        # Validate input
        for k, v in self.config.get("inputs", {}).items():
            # Set default values
            variable_value = inputs.get(k)

            if inputs.get(k) is None:
                inputs[k] = v.get("default")

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
                    inputs[k] = float(variable_value)

                if variable_type == "integer":
                    inputs[k] = int(variable_value)

                if variable_type == "string":
                    inputs[k] = str(variable_value)

                if variable_type == "boolean":
                    inputs[k] = bool(variable_value)

        if self.step is not None:
            # Update steps output after casting.
            await self.step.update(inputs=inputs)

        logger.debug(f"Inputs for '{self.full_name}': {json.dumps(inputs)}")

        output = (await self.runner.run(inputs)) or {}

        logger.info(f"Finished running '{self.full_name}'")
        logger.debug(f"Outputs for '{self.full_name}': {json.dumps(output)}")
        return output

    @property
    def full_name(self) -> str:
        return f"{self.name} v{self.version}"
