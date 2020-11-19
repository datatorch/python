from datatorch.utils.objects import deep_merge
import typing
import platform
from typing import Dict, Union, cast
from jinja2 import Template
from datatorch.agent.client import AgentJobConfig, AgentRunConfig
from ..directory import agent_directory


if typing.TYPE_CHECKING:
    from .step import Step
    from .action import Action


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


def create_variables_mock(job: Union[AgentJobConfig, dict] = {}):
    """ Merges config with mocked data."""
    run: AgentRunConfig = {
        "id": "run-id",
        "name": "Action Name Mock",
        "text": "Mocked Config",
        "config": {"mock": True},
        "runNumber": -1,
        "pipeline": {
            "id": "pipeline-id",
            "creatorId": "mocked",
            "projectId": "project-id",
            "lastRunNumber": -1,
        },
        "trigger": {
            "id": "trigger-id",
            "type": "local-trigger",
            "event": {},
        },
    }
    result = deep_merge(
        {
            "id": "job-id",
            "name": "Local Action Job",
            "run": run,
            "steps": [],
        },
        job,
    )
    return Variables(cast(AgentJobConfig, result))


class Variables(object):
    """
    Instigated before each Job.
    """

    def __init__(self, job: AgentJobConfig):
        self.variables: Dict[str, dict] = {"variable": {}, "input": {}}
        self.set(
            "job",
            {
                "id": job.get("id"),
                "name": job.get("name"),
            },
        )
        run = job.get("run")
        run_id = run.get("id")
        self.set(
            "run",
            {
                "id": run_id,
                "name": run.get("name"),
                "config": run.get("config"),
                "createdAt": run.get("createdAt"),
                "runNumber": run.get("runNumber"),
                "directory": agent_directory.run_dir(run_id),
            },
        )

        pipeline = run.get("pipeline")
        self.set(
            "pipeline",
            {
                "id": pipeline.get("id"),
                "name": pipeline.get("name"),
                "creatorId": pipeline.get("creatorId"),
                "projectId": pipeline.get("projectId"),
                "lastRunNumber": pipeline.get("lastRunNumber"),
            },
        )

        trigger_run = run.get("trigger", {})
        trigger = trigger_run.get("trigger", {})
        self.set("trigger", trigger)

        event = trigger_run.get("event", {})
        self.set("event", event)
        self.set("input", event)
        self.set("variable", event)

    def set_step(self, step: "Step"):
        self.set("step", {"id": step.id, "name": step.name})

    def set_action(self, action: "Action"):
        action.full_name
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
        # If input is a string, run it though render as it might contain variables.
        value = self.render(value) if isinstance(value, str) else value
        self.variables["variable"][key] = value
        self.variables["input"][key] = value

    def set(self, section: str, variables: dict):
        self.variables[section] = variables

    def merge(self, section: str, variables: dict):
        self.variables[section] = {**self.variables[section], **variables}

    def render(self, string: str):
        tp = Template(
            string,
            block_start_string="${%",
            variable_start_string="${{",
            comment_start_string="${#",
        )
        return tp.render({**global_variables, **self.variables})

    @property
    def inputs(self) -> dict:
        return self.variables.get("variable", {})
