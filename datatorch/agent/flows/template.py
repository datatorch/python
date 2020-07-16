import platform

from jinja2 import Template
import typing


if typing.TYPE_CHECKING:
    from .job import Job
    from .step import Step
    from .action import Action


global_variables = {
    "machine": {
        "name": platform.machine(),
        "os": platform.system(),
        "version": platform.version(),
    },
    "python": {
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
    },
}


class Variables(object):
    def __init__(self, flow_run: dict):
        self.variables = {"variable": {}, "input": {}}
        flow = flow_run.get("flow")
        self.set(
            "flow",
            {
                "id": flow.get("id"),
                "name": flow.get("name"),
                "creatorId": flow.get("creatorId"),
                "projectId": flow.get("projectId"),
                "lastRunNumber": flow.get("lastRunNumber"),
            },
        )

        self.set(
            "run",
            {
                "id": flow_run.get("id"),
                "name": flow_run.get("name"),
                "config": flow_run.get("config"),
                "createdAt": flow_run.get("createdAt"),
                "runNumber": flow_run.get("runNumber"),
            },
        )
        print(self.variables)

    def set_job(self, job: "Job"):
        """ Setup job related variables """
        self.set(
            "job", {"id": job.id, "directory": job.dir, "name": job.config.get("name"),}
        )

    def set_step(self, step: "Step"):
        self.set("step", {"id": step.id, "name": step.name})

    def set_action(self, action: "Action"):
        self.set(
            "action",
            {"name": action.name, "directory": action.dir, "version": action.version},
        )

    def add_input(self, key: str, value):
        # If input is a string, render any variables
        value = self.render(value) if isinstance(value, str) else value
        self.variables["variable"][key] = value
        self.variables["input"][key] = value

    def set(self, section: str, variables: dict):
        self.variables[section] = variables

    def merge(self, section: str, variables: dict):
        self.variables[section] = {**self.variables[section], **variables}

    def render(self, string: str):
        tp = Template(string)
        return tp.render({**global_variables, **self.variables})

    @property
    def inputs(self) -> dict:
        return self.variables.get("variable", {})
