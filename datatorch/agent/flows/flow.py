import os
import yaml
import logging
from typing import List, Union
from .job import Job


logger = logging.getLogger(__name__)


class Flow(object):
    @classmethod
    def from_yaml(cls, path):
        with open(path, "r") as config_file:
            config = yaml.load(config_file, Loader=yaml.FullLoader)
        name = config.get("name") or os.path.splitext(os.path.basename(path))[0]
        jobs = Job.from_dict(config.get("jobs", {}))
        return Flow(name=name, jobs=jobs)

    def __init__(self, name: str, jobs: List[Job]):
        self.name = name
        self.jobs = jobs
        self.current_job = 0

    def run(self, job: Union[str, int, Job]):
        if isinstance(job, str):
            job = [x for x in self.jobs if x.name == job]

        if isinstance(job, int):
            job = self.jobs[job]

        if isinstance(job, Job):
            job.run()
