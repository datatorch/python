"""A dispatched step tells its action where it sits in the record (0.8.1):
`${{ run.* }}` in the action's templates and DATATORCH_PROJECT_ID /
DATATORCH_RUN_ID / DATATORCH_PIPELINE_ID / DATATORCH_STEP_ID in the
process environment of whatever the action runs."""

import os

from datatorch.core import env as env_names
from datatorch.runner.pipelines.step.step import Step
from datatorch.runner.pipelines.template import Variables
from datatorch.runner.pipelines.runner.runner import Runner

DISPATCH = {
    "stepId": "step-1",
    "runnerId": "runner-1",
    "action": "datatorch-actions/claude-chat@v4",
    "stepName": "Turn",
    "stepIndex": 0,
    "input": {"message": "hi"},
    "jobId": "job-1",
    "jobName": "chat",
    "runId": "run-1",
    "runNumber": 7,
    "pipelineId": "pipe-1",
    "projectId": "proj-1",
}


def test_run_namespace_from_dispatch():
    step = Step.from_dispatch(DISPATCH)
    variables = Variables()
    variables.set_step(step)
    assert variables.render("${{ run.projectId }}") == "proj-1"
    assert variables.render("${{ run.id }}/${{ run.number }}") == "run-1/7"
    assert variables.render("${{ run.pipelineId }}") == "pipe-1"
    assert variables.render("${{ step.id }}") == "step-1"


def test_run_namespace_empty_in_local_mode():
    step = Step.from_dict({"id": "local", "action": "x/y@v1", "name": "n"})
    variables = Variables()
    variables.set_step(step)
    assert variables.variables["run"]["projectId"] is None


def test_runner_env_carries_identity(monkeypatch):
    for name in (
        env_names.PROJECT_ID,
        env_names.RUN_ID,
        env_names.PIPELINE_ID,
        env_names.STEP_ID,
    ):
        monkeypatch.setenv(name, "stale")  # never inherited from the outer process
    step = Step.from_dispatch(DISPATCH)
    variables = Variables()
    variables.set_step(step)
    runner = Runner({}, action=None)
    runner.variables = variables
    env = runner.runner_env()
    assert env[env_names.PROJECT_ID] == "proj-1"
    assert env[env_names.RUN_ID] == "run-1"
    assert env[env_names.PIPELINE_ID] == "pipe-1"
    assert env[env_names.STEP_ID] == "step-1"


def test_runner_env_without_variables_sets_nothing():
    env = Runner({}, action=None).runner_env()
    assert env_names.PROJECT_ID not in env
