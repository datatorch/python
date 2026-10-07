"""
Local-mode port of the server's step input resolver.

When a pipeline runs against the DataTorch server, the server resolves
``${{ steps.<name>.output.<key> }}``, ``${{ input.<key> }}`` and
``${{ jobs.<name>.outputs.<key> }}`` references before dispatching each
step. Local mode (``datatorch pipeline run``) replicates those exact
semantics so a pipeline yaml behaves identically in both places:

- A reference spanning the whole string resolves to the raw value
  (numbers/objects preserved); embedded references interpolate as strings.
- ``outputs``/``inputs`` are accepted as aliases of ``output``/``input``.
- Unresolvable references are an error (strict — matching the server,
  which fails the step at dispatch).

Cross-job note: ``${{ jobs.<name>.outputs.<key> }}`` is recognized as a
server namespace here for parity, but local mode runs a single job at a
time (there is no cross-job sequencer — see ``job.Job``), so no job
outputs are supplied and such a reference resolves as unresolvable, i.e.
raises rather than passing a literal ``${{ }}`` to the action. A yaml that
uses job dependencies is a server-executed workflow.
"""

import json
import re
from typing import Any, Dict, List, Set, Tuple

# Named groups so the combined alternation reads by name, not by positional
# index that shifts when a namespace is added — mirrors the server resolver.
# The name group is ``[^}]+?`` (not ``.+?``) so it can't backtrack across a
# ``}}`` boundary — a string that both starts and ends with a ref must not be
# mistaken for one spanning ref.
STEP_REF = (
    r"\$\{\{\s*steps\.(?P<stepName>[^}]+?)\.outputs?\.(?P<stepKey>[\w.\-]+)\s*\}\}"
)
INPUT_REF = r"\$\{\{\s*inputs?\.(?P<inputKey>[\w.\-]+)\s*\}\}"
JOB_REF = r"\$\{\{\s*jobs\.(?P<jobName>[^}]+?)\.outputs?\.(?P<jobKey>[\w.\-]+)\s*\}\}"

SERVER_REF = re.compile(f"{STEP_REF}|{INPUT_REF}|{JOB_REF}")
WHOLE_STRING_REF = re.compile(f"^(?:{STEP_REF}|{INPUT_REF}|{JOB_REF})$")

_MISSING = object()


class UnresolvedReferenceError(Exception):
    def __init__(self, refs: List[str]):
        self.refs = refs
        super().__init__(
            "Unresolvable input reference(s): "
            + ", ".join(refs)
            + ". References must point to a named earlier step output, "
            + "a trigger input, or a needed job output."
        )


def _lookup_mapping(mapping: Dict[str, dict], name, key):
    if name is None or key is None:
        return _MISSING
    values = mapping.get(name.strip(), _MISSING)
    if values is _MISSING or not isinstance(values, dict):
        return _MISSING
    return values.get(key, _MISSING)


def _lookup(
    outputs_by_name: Dict[str, dict],
    trigger_input: dict,
    job_outputs_by_name: Dict[str, dict],
    groups: Dict[str, Any],
):
    step = _lookup_mapping(
        outputs_by_name, groups.get("stepName"), groups.get("stepKey")
    )
    if groups.get("stepName") is not None:
        return step
    job = _lookup_mapping(
        job_outputs_by_name, groups.get("jobName"), groups.get("jobKey")
    )
    if groups.get("jobName") is not None:
        return job
    input_key = groups.get("inputKey")
    if input_key is not None:
        return trigger_input.get(input_key, _MISSING)
    return _MISSING


def _resolve(
    value, outputs_by_name, trigger_input, job_outputs_by_name, misses: Set[str]
):
    if isinstance(value, str):
        whole = WHOLE_STRING_REF.match(value)
        if whole:
            resolved = _lookup(
                outputs_by_name,
                trigger_input,
                job_outputs_by_name,
                whole.groupdict(),
            )
            if resolved is _MISSING:
                misses.add(value.strip())
                return value
            return resolved

        def replace(match: "re.Match") -> str:
            resolved = _lookup(
                outputs_by_name,
                trigger_input,
                job_outputs_by_name,
                match.groupdict(),
            )
            if resolved is _MISSING:
                misses.add(match.group(0))
                return match.group(0)
            if isinstance(resolved, (dict, list)):
                return json.dumps(resolved)
            if isinstance(resolved, bool):
                # Match the server's String(true|false)
                return "true" if resolved else "false"
            return str(resolved)

        return SERVER_REF.sub(replace, value)
    if isinstance(value, list):
        return [
            _resolve(v, outputs_by_name, trigger_input, job_outputs_by_name, misses)
            for v in value
        ]
    if isinstance(value, dict):
        return {
            k: _resolve(v, outputs_by_name, trigger_input, job_outputs_by_name, misses)
            for k, v in value.items()
        }
    return value


def resolve_step_input(
    inputs: Any,
    outputs_by_name: Dict[str, dict],
    trigger_input: dict = {},
    job_outputs_by_name: Dict[str, dict] = {},
) -> Tuple[Any, List[str]]:
    """Deep-resolve server-namespace references in a step's inputs.

    Returns ``(resolved, unresolved)`` where ``unresolved`` lists the
    references (as authored) that could not be resolved. ``job_outputs_by_name``
    is empty in local mode (single-job execution), so ``${{ jobs.* }}``
    references resolve as unresolvable.
    """
    misses: Set[str] = set()
    resolved = _resolve(
        inputs,
        outputs_by_name,
        trigger_input or {},
        job_outputs_by_name or {},
        misses,
    )
    return resolved, sorted(misses)
