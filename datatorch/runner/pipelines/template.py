import json
import platform
import re
import typing
import uuid
from typing import Dict, List, Tuple
from jinja2 import Environment, Template, meta
from jinja2.exceptions import TemplateSyntaxError
from ..directory import runner_directory

if typing.TYPE_CHECKING:
    from .step import Step
    from .action import Action


# A shell command/script template referencing the resolved-input namespaces
# anywhere inside a ${{ }} expression or ${% %} block — as a namespace root
# (`input` / `variable`, not `x.input`). These values may hold untrusted
# data (trigger payloads, fetched step outputs); splicing them into a shell
# string is command injection, so shell/cmd runners must read them from
# $INPUT_<NAME> env vars instead.
_INPUT_REF_IN_TEMPLATE = re.compile(r"\$\{[{%][^}]*?(?<![.\w])(?:input|variable)(?!\w)")

# One `${{ ... }}` expression, as written. Used to find the expressions in
# a string before rendering so that the ones the runner does not own can
# be kept exactly as they are (see `Variables.render`).
_EXPRESSION = re.compile(r"\$\{\{.*?\}\}", re.DOTALL)

_environment = Environment(
    block_start_string="${%",
    variable_start_string="${{",
    comment_start_string="${#",
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


_runner_namespace = {
    "id": runner_directory.settings.runner_id,
    "directory": runner_directory.dir,
}

global_variables = {
    # `${{ runner.* }}` is the spelling since October 2026; `agent.*` is
    # the same namespace under its pre-rename name, kept for existing
    # action yaml.
    "runner": _runner_namespace,
    "agent": _runner_namespace,
    "directory": {
        "runner": runner_directory.dir,
        "agent": runner_directory.dir,
        "actions": runner_directory.actions_dir,
        "logs": runner_directory.logs_dir,
        "temp": runner_directory.temp_dir,
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

# The namespaces the runner renders (`run` since 0.8.1: the step's place
# in the record). `${{ ... }}` text rooted anywhere else (`steps.*`,
# `inputs.*`, `jobs.*`, `secrets.*`, unknown names) is not a reference
# the runner can resolve: the server resolves its own namespaces before
# dispatch, and whatever still reads like one in a step input is DATA (a
# log line, a fetched body, an older error message) that must reach the
# action untouched.
RUNNER_NAMESPACES = frozenset(
    {*global_variables.keys(), "input", "variable", "step", "action", "run"}
)


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
    - ``run`` — the run the step belongs to (id, number, projectId,
      pipelineId, jobId); empty values in local mode
    - ``input`` / ``variable`` — the step's own (already-resolved) inputs,
      for use inside the action's own templates (``runs.command`` etc.).
      ``variable`` is a legacy alias of ``input``; both are scoped to the
      one step. The old job-wide accumulating namespace is gone.

    Everything else is inert. A ``${{ ... }}`` whose root names are not all
    in ``RUNNER_NAMESPACES`` (or that does not parse) is left exactly as
    written, never raising and never rewritten: the runner does not author
    that text, so it must not interpret it. Only string inputs are rendered;
    objects and arrays pass through as they arrive.
    """

    def __init__(self):
        inputs: Dict[str, typing.Any] = {}
        # `variable` aliases `input` (same dict object) for action compat.
        self.variables: Dict[str, dict] = {"variable": inputs, "input": inputs}

    def set_step(self, step: "Step"):
        self.set("step", {"id": step.id, "name": step.name})
        # Where the step sits in the record (server mode; empty when run
        # locally). `${{ run.projectId }}` in an action's own templates, and
        # DATATORCH_PROJECT_ID / DATATORCH_RUN_ID in its environment.
        self.set(
            "run",
            {
                "id": getattr(step, "run_id", None),
                "number": getattr(step, "run_number", None),
                "projectId": getattr(step, "project_id", None),
                "pipelineId": getattr(step, "pipeline_id", None),
                "jobId": getattr(step, "job_id", None),
            },
        )

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
        """Render the runner's own namespaces in ``string``; keep every
        other ``${{ ... }}`` exactly as written (see the class docstring).
        """
        if string is None or "${" not in string:
            return string
        protected, kept = self._protect_foreign_expressions(string)
        try:
            rendered = self._template(protected).render(
                {**global_variables, **self.variables}
            )
        except TemplateSyntaxError:
            # Not a template the runner can read (an unclosed `${{`, a
            # stray `${%` in data): it is text, hand it back as it came.
            return string
        for token, text in kept:
            rendered = rendered.replace(token, text)
        return rendered

    @classmethod
    def _protect_foreign_expressions(
        cls, string: str
    ) -> Tuple[str, List[Tuple[str, str]]]:
        """Swap each ``${{ ... }}`` the runner does not own for an opaque
        token so Jinja never sees it; the caller restores them after
        rendering. Returns the protected string and the (token, original
        text) pairs."""
        nonce = uuid.uuid4().hex
        kept: List[Tuple[str, str]] = []

        def swap(match: "re.Match[str]") -> str:
            text = match.group(0)
            if cls._owns(text):
                return text
            token = f"\x00{nonce}:{len(kept)}\x00"
            kept.append((token, text))
            return token

        return _EXPRESSION.sub(swap, string), kept

    @staticmethod
    def _owns(expression: str) -> bool:
        """True when ``expression`` (one ``${{ ... }}``) parses and every
        name it reads is one of the runner's namespaces."""
        try:
            ast = _environment.parse(expression)
        except TemplateSyntaxError:
            return False
        return meta.find_undeclared_variables(ast) <= RUNNER_NAMESPACES

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
            k: v for k, v in self.variables.items() if k not in ("input", "variable")
        }
        return self._template(string).render({**global_variables, **context})

    def env_inputs(self) -> Dict[str, str]:
        """Resolved step inputs as ``INPUT_<NAME>`` env vars — the
        injection-safe channel for shell/cmd runners."""
        return {_env_key(k): _stringify_env(v) for k, v in self.inputs.items()}

    @staticmethod
    def _template(string: str) -> Template:
        return _environment.from_string(string)

    @property
    def inputs(self) -> dict:
        return self.variables.get("input", {})
