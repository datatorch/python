"""
Inputs reach a python action as one JSON argv argument, and actions live
under the agent directory, which on macOS is inside "Application Support".
Both must survive the shell untouched: the runner used to hand-escape
them, which turned every apostrophe in an input into a double quote and
broke script paths containing a space.
"""

import asyncio
import os
import tempfile

from datatorch.agent.pipelines.runner.python import PythonRunner
from datatorch.agent.pipelines.runner.shell import ShellRunner


class _FakeVariables:
    def __init__(self, inputs):
        self.inputs = inputs

    def render(self, value):
        return value

    def render_command(self, value):
        return value

    def env_inputs(self):
        return {f"INPUT_{k.upper()}": str(v) for k, v in self.inputs.items()}


class _FakeAction:
    step = None

    def __init__(self, directory):
        self.dir = directory


def _action_dir() -> str:
    # A space in the path, like ~/Library/Application Support/DataTorch.
    path = os.path.join(tempfile.mkdtemp(prefix="datatorch-test-"), "App Support")
    os.makedirs(path)
    return path


AWKWARD_INPUTS = {
    "message": "what's up? it's \"quoted\", $HOME, `whoami`, $(id), a\\b, 100%\nline two\ttab",
    "unicode": "café — 日本語 'single' \"double\"",
    "empty": "",
    "count": 3,
    "items": ["it's", "fine"],
}


def test_python_runner_passes_inputs_verbatim():
    directory = _action_dir()
    with open(os.path.join(directory, "main.py"), "w") as f:
        f.write(
            "import json, sys\n"
            "print('::echo::' + json.dumps(json.loads(sys.argv[-1])))\n"
        )

    runner = PythonRunner({"main": "main.py"}, _FakeAction(directory))
    outputs = asyncio.run(runner.run(_FakeVariables(dict(AWKWARD_INPUTS))))

    assert outputs["echo"] == AWKWARD_INPUTS


def test_shell_runner_script_path_with_space():
    directory = _action_dir()
    with open(os.path.join(directory, "run.sh"), "w") as f:
        f.write('#!/bin/sh\necho "::args::$#"\necho "::first::\\"$1\\""\n')

    runner = ShellRunner({"script": "run.sh hello"}, _FakeAction(directory))
    outputs = asyncio.run(runner.run(_FakeVariables({})))

    assert outputs == {"args": 1, "first": "hello"}


def test_shell_runner_inputs_arrive_as_env():
    directory = _action_dir()
    with open(os.path.join(directory, "run.sh"), "w") as f:
        f.write(
            "#!/bin/sh\n"
            'printf \'::message::%s\\n\' "$(printf %s "$INPUT_MESSAGE" | '
            "python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')\"\n"
        )

    runner = ShellRunner({"script": "run.sh"}, _FakeAction(directory))
    message = 'it\'s "fine" $HOME'
    outputs = asyncio.run(runner.run(_FakeVariables({"message": message})))

    assert outputs["message"] == message
