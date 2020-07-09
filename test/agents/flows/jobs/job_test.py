import pytest
import unittest

from datatorch.agent.flows.job import Job


class JobParsingTest(unittest.TestCase):
    def test_empty_job(self):
        config = {"test": {}}
        with pytest.raises(AssertionError):
            Job.from_dict(config)

    def test_no_jobs(self):
        config = {}
        jobs = Job.from_dict(config)
        assert len(jobs) == 0

    def test_job_zero_steps(self):
        config = {"test": {"steps": []}}
        with pytest.raises(AssertionError):
            Job.from_dict(config)

    def test_reads_jobs(self):
        config = {"test": {"steps": [{"name": "test", "action": "example/test@1"}]}}
        jobs = Job.from_dict(config)
        assert len(jobs) == 1
        assert jobs[0].name == "test"
        assert len(jobs[0].steps) == 1
