"""
Local-mode acceptance test: a two-step job where step 2 consumes step 1's
output via the canonical ``${{ steps.<name>.output.<key> }}`` syntax —
the same dataflow the server orchestrator drives in production, exercised
through the cmd runner's ``::key::value`` output protocol.
"""
import asyncio
import os
import unittest

import yaml

from datatorch.agent.directory import agent_directory
from datatorch.agent.pipelines.job import Job
from datatorch.agent.pipelines.resolver import UnresolvedReferenceError


def install_action(name: str, version: str, config: dict):
    """Pre-place an action in the (test-isolated) local action cache so
    no git download is attempted."""
    action_dir = agent_directory.action_dir(name, version)
    os.makedirs(action_dir, exist_ok=True)
    with open(os.path.join(action_dir, "action-datatorch.yaml"), "w") as f:
        yaml.dump(config, f)


install_action(
    "local-test/count",
    "v1",
    {
        "name": "Count",
        "outputs": {"total": {"type": "integer"}},
        "runs": {"using": "cmd", "command": "echo ::total::42"},
    },
)

install_action(
    "local-test/report",
    "v1",
    {
        "name": "Report",
        "inputs": {"total": {"type": "integer", "required": True}},
        # Inputs reach the command as $INPUT_<NAME> env vars, never spliced
        # into the shell string (injection policy). The pipeline-yaml step
        # `inputs` below still use ${{ ... }} — those are resolved to values
        # server/job-side and delivered here as $INPUT_TOTAL.
        "runs": {"using": "cmd", "command": "echo ::echoed::$INPUT_TOTAL"},
    },
)


class TestLocalPipeline(unittest.TestCase):
    def test_two_step_job_with_steps_reference(self):
        job = Job(
            {
                "name": "process",
                "steps": [
                    {"name": "Count", "action": "local-test/count@v1"},
                    {
                        "name": "Report",
                        "action": "local-test/report@v1",
                        "inputs": {"total": "${{ steps.Count.output.total }}"},
                    },
                ],
            }
        )
        outputs = asyncio.run(job.run())
        self.assertEqual(outputs["Count"], {"total": 42})
        self.assertEqual(outputs["Report"], {"echoed": 42})

    def test_unresolvable_reference_fails_the_job(self):
        job = Job(
            {
                "name": "broken",
                "steps": [
                    {
                        "name": "Report",
                        "action": "local-test/report@v1",
                        "inputs": {"total": "${{ steps.Nope.output.total }}"},
                    },
                ],
            }
        )
        with self.assertRaises(UnresolvedReferenceError):
            asyncio.run(job.run())

    def test_trigger_input_reference(self):
        job = Job(
            {
                "name": "with-input",
                "steps": [
                    {
                        "name": "Report",
                        "action": "local-test/report@v1",
                        "inputs": {"total": "${{ input.total }}"},
                    },
                ],
            },
            trigger_input={"total": 7},
        )
        outputs = asyncio.run(job.run())
        self.assertEqual(outputs["Report"], {"echoed": 7})
