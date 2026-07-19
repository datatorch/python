import json
import platform
import re
import typing
from typing import Dict
from jinja2 import Template
from ..directory import agent_directory

if typing.TYPE_CHECKING:
    from .step import Step
    from .action import Action


# A shell command/script template referencing the resolved-input namespaces
# anywhere inside a ${{ }} expression or ${% %} block — as a namespace root
# (`input` / `variable`, not `x.input`). These values may hold untrusted
# data (trigger payloads, fetched step outputs); splicing them into a shell
# string is command injection, so shell/cmd runners must read them from
# $INPUT_<NAME> env vars instead.
_INPUT_REF_IN_TEMPLATE = re.compile(
    r"\$\{[{%][^}]*?(?<![.\w])(?:input|variable)(?!\w)"
)


class InputInjectionError(Exception):
    """Raised when a shell command/script interpolates ${{ input.* }} /
    ${{ variable.* }} — forbidden by the DataTorch injection policy
    (docs/Pipelines.md). Inputs reach shell actions as $INPUT_<NAME>."""


def _stringify_env(value) -> str:
    """Render a resolved input value for a shell environment variable.
    Objects/arrays arrive JSON-encoded; booleans use shell-friendly
    lowercase; None is the empty string."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def _env_key(key: str) -> str:
    return "INPUT_" + re.sub(r"[^A-Z0-9]", "_", key.upper())


global_variables = {
    "agent": {
        "id": agent_directory.settings.agent_id,
        "directory": agent_directory.dir,
    },
    "directory": {
        "agent": agent_directory.dir,
        "actions": agent_directory.actions_dir,
        "logs": agent_directory.logs_dir,
        "temp": agent_directory.temp_dir,
    },
    "machine": {
        "name": platform.node(),
        "os": platform.system(),
        "version": platform.version(),
    },
    "python": {
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
    },
}


class Variables(object):
    """
    Machine-local template context for a single step (agent protocol v2).

    Cross-step dataflow (``${{ steps.<name>.output.<key> }}``) and trigger
    inputs (``${{ input.<key> }}`` in the pipeline yaml) are resolved by the
    SERVER before a step is dispatched — the agent receives concrete values
    and never sees other steps' outputs.

    What renders here is strictly local:

    - ``agent``, ``directory``, ``machine``, ``python`` — machine facts
    - ``step``, ``action`` — the step being executed
    - ``input`` / ``variable`` — the step's own (already-resolved) inputs,
      for use inside the action's own templates (``runs.command`` etc.).
      ``variable`` is a legacy alias of ``input``; both are scoped to the
      one step. The old job-wide accumulating namespace is gone.
    """

    def __init__(self):
        inputs: Dict[str, typing.Any] = {}
        # `variable` aliases `input` (same dict object) for action compat.
        self.variables: Dict[str, dict] = {"variable": inputs, "input": inputs}

    def set_step(self, step: "Step"):
        self.set("step", {"id": step.id, "name": step.name})

    def set_action(self, action: "Action"):
        self.set(
            "action",
            {
                "name": action.name,
                "directory": action.dir,
                "version": action.version,
                "tag": action.version,
                "description": action.description,
            },
        )

    def add_input(self, key: str, value):
        # If input is a string, run it though render as it might contain
        # machine-local variables.
        value = self.render(value) if isinstance(value, str) else value
        self.variables["input"][key] = value

    def set(self, section: str, variables: dict):
        self.variables[section] = variables

    def merge(self, section: str, variables: dict):
        self.variables[section] = {**self.variables[section], **variables}

    def render(self, string: str):
        tp = self._template(string)
        return tp.render({**global_variables, **self.variables})

    def render_command(self, string: str):
        """Render a shell command/script template.

        Machine-local and step/action namespaces only — the ``input`` /
        ``variable`` namespaces are DELIBERATELY out of scope. Resolved
        step inputs (which may carry untrusted trigger/step-output data)
        reach shell actions as ``$INPUT_<NAME>`` environment variables,
        never spliced into the command string as code. Referencing
        ``${{ input.* }}`` / ``${{ variable.* }}`` here is a hard error.
        See the injection policy in docs/Pipelines.md.
        """
        if string is None:
            return None
        if _INPUT_REF_IN_TEMPLATE.search(string):
            raise InputInjectionError(
                "Shell actions must read inputs from environment variables "
                '(e.g. "$INPUT_MESSAGE"), not ${{ input.message }} / '
                "${{ variable.message }} in the command — resolved inputs "
                "can carry untrusted data and interpolating them into a "
                "shell command is an injection risk. (DataTorch injection "
                "policy; see docs/Pipelines.md.)"
            )
        context = {
            k: v
            for k, v in self.variables.items()
            if k not in ("input", "variable")
        }
        return self._template(string).render({**global_variables, **context})

    def env_inputs(self) -> Dict[str, str]:
        """Resolved step inputs as ``INPUT_<NAME>`` env vars — the
        injection-safe channel for shell/cmd runners."""
        return {_env_key(k): _stringify_env(v) for k, v in self.inputs.items()}

    @staticmethod
    def _template(string: str) -> Template:
        return Template(
            string,
            block_start_string="${%",
            variable_start_string="${{",
            comment_start_string="${#",
        )

    @property
    def inputs(self) -> dict:
        return self.variables.get("input", {})
