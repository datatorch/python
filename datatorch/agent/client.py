from datatorch.api.api import ApiClient
from typing import AsyncGenerator, List, cast
from gql import gql
from .directory import agent_directory
from gql.client import AsyncClientSession

from typing_extensions import TypedDict


class Log(TypedDict):
    createdAt: str
    message: str


class AgentPipelineConfig(TypedDict):
    id: str
    projectId: str
    creatorId: str
    lastRunNumber: int


class AgentStepsConfig(TypedDict):
    id: str
    name: str
    action: str
    index: int


class AgentTriggerConfig(TypedDict):
    id: str
    type: str
    event: dict


class AgentRunConfig(TypedDict):
    id: str
    name: str
    text: str
    config: dict
    runNumber: int
    pipeline: AgentPipelineConfig
    trigger: AgentTriggerConfig


class AgentJobConfig(TypedDict):
    id: str
    name: str
    run: AgentRunConfig
    steps: List[AgentStepsConfig]


class AgentRequestConfig(TypedDict):
    job: AgentJobConfig


class AgentApiClient(object):
    def __init__(self, session: AsyncClientSession):
        self.session = session

    def agent_jobs(self):
        """ Subscriptions to the agent job assignment namespace. """
        # fmt: off
        sub = gql("""
            subscription {
                job: agentJobs {
                    id
                    name
                    run {
                        id
                        name
                        text
                        config
                        runNumber
                        pipeline {
                            id
                            projectId
                            creatorId
                            lastRunNumber
                        }
                        trigger {
                            id
                            trigger {
                                id
                                type
                                config
                            }
                            event
                        }
                    }
                    steps {
                        id
                        name
                        index
                        action
                    }
                }
            }
        """)
        # fmt: on
        return cast(
            AsyncGenerator[AgentRequestConfig, None], self.session.subscribe(sub)
        )

    def initial_metrics(self, metrics):
        # fmt: off
        mutate = """
            mutation updateAgent(
                $id: ID!
                $version: String
                $os: String
                $osRelease: String
                $osVersion: String
                $pythonVersion: String
                $totalMemory: Int
                $cpuName: String
                $cpuFreqMin: Float
                $cpuFreqMax: Float
                $cpuCoresPhysical: Int
                $cpuCoresLogical: Int
            ) {
                updateAgent(id: $id, input: {
                    version: $version
                    os: $os
                    osRelease: $osRelease
                    osVersion: $osVersion
                    pythonVersion: $pythonVersion
                    totalMemory: $totalMemory
                    cpuName: $cpuName
                    cpuFreqMin: $cpuFreqMin
                    cpuFreqMax: $cpuFreqMax
                    cpuCoresPhysical: $cpuCoresPhysical
                    cpuCoresLogical: $cpuCoresLogical
                }) {
                    id
                }
            }
        """
        # fmt: on
        params = {"id": agent_directory.settings.agent_id, **metrics}
        return self.execute(gql(mutate), params=params)

    def metrics(self, metrics):
        # fmt: off
        mutate = """
            mutation updateAgent(
                $agentId: ID!
                $sampledAt: DateTime!
                $avgLoad1: Float
                $avgLoad5: Float
                $avgLoad15: Float
                $cpuUsage: Float
                $diskUsage: Float
                $memoryUsage: Float
            ) {
                createAgentMetric(input: {
                    agentId: $agentId
                    sampledAt: $sampledAt
                    avgLoad1: $avgLoad1
                    avgLoad5: $avgLoad5
                    avgLoad15: $avgLoad15
                    cpuUsage: $cpuUsage
                    diskUsage: $diskUsage
                    memoryUsage: $memoryUsage
                }) {
                    id
                }
            }
        """
        # fmt: on
        params = {"agentId": agent_directory.settings.agent_id, **metrics}
        return self.execute(mutate, params=params)

    def update_step(self, values: dict):
        # fmt: off
        mutate = """
            mutation UpdateStepRun(
                $id: ID!
                $inputs: JSON
                $outputs: JSON
                $status: PipelineStepStatus
                $startedAt: DateTime
                $finishedAt: DateTime
            ) {
                updatePipelineStep(
                    id: $id
                    input: {
                        status: $status
                        output: $outputs
                        input: $inputs
                        startedAt: $startedAt
                        finishedAt: $finishedAt
                    }
                )
            }
        """
        # fmt: on
        return self.execute(mutate, params=values)

    async def update_job(self, values: dict):
        # fmt: off
        mutate = """
            mutation UpdateJob($id: ID!, $status: PipelineJobStatus) {
                updatePipelineJobRun(
                    id: $id,
                    input: { status: $status }
                )
            }
        """
        # fmt: on
        return await self.execute(mutate, params=values)

    def upload_step_logs(self, step_id: str, logs: List[Log]):
        # fmt: off
        mutate = """
            mutation UploadStepLogs($id: ID!, $logs: [CreatePipelineStepLog!]!) {
                createPipelineStepLog(stepId: $id, logs: $logs)
            }
        """
        # fmt: on
        return self.execute(mutate, params={"id": step_id, "logs": logs})

    async def execute(self, query, *args, params: dict = {}, **kwargs) -> dict:
        """ Wrapper around execute """
        removed_none = dict((k, v) for k, v in params.items() if v is not None)
        if type(query) == str:
            query = gql(query)
        return await self.session.execute(
            query, *args, variable_values=removed_none, **kwargs
        )


def create_client():
    ApiClient
