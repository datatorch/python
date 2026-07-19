from typing import AsyncGenerator, List, Optional, cast
from gql import gql
from .directory import agent_directory
from gql.client import AsyncClientSession

from typing_extensions import TypedDict


class Log(TypedDict):
    createdAt: str
    message: str


class AgentStepDispatch(TypedDict):
    """A ready step pushed to this agent (agent protocol v2).

    ``input`` arrives server-resolved: ``steps.*`` and ``input.*``
    references are already substituted with concrete values.
    """

    stepId: str
    agentId: str
    action: str
    stepName: Optional[str]
    stepIndex: int
    input: dict
    jobId: str
    jobName: str
    runId: str
    runNumber: int
    pipelineId: str
    projectId: str


class AgentStepRequest(TypedDict):
    step: AgentStepDispatch


class AgentStepCancel(TypedDict):
    """A stop signal for a step this agent is currently running."""

    stepId: str
    agentId: str


class AgentStepCancelRequest(TypedDict):
    cancel: AgentStepCancel


STEP_DISPATCH_FIELDS = """
    stepId
    agentId
    action
    stepName
    stepIndex
    input
    jobId
    jobName
    runId
    runNumber
    pipelineId
    projectId
"""


class AgentApiClient(object):
    def __init__(self, session: AsyncClientSession):
        self.session = session

    def agent_steps(self):
        """Subscribe to ready steps dispatched to this agent."""
        # fmt: off
        sub = gql("""
            subscription {
                step: agentSteps {
                    %s
                }
            }
        """ % STEP_DISPATCH_FIELDS)
        # fmt: on
        return cast(
            AsyncGenerator[AgentStepRequest, None], self.session.subscribe(sub)
        )

    def agent_step_cancels(self):
        """Subscribe to stop signals for steps this agent is running.

        Best effort: the server has already moved the step terminal, so a
        missed signal only means the step runs to harmless completion.
        """
        # fmt: off
        sub = gql("""
            subscription {
                cancel: agentStepCancels {
                    stepId
                    agentId
                }
            }
        """)
        # fmt: on
        return cast(
            AsyncGenerator[AgentStepCancelRequest, None],
            self.session.subscribe(sub),
        )

    async def pending_steps(self) -> List[AgentStepDispatch]:
        """Steps dispatched to this agent but not yet claimed.

        Called on (re)connect: pushes missed while offline are recovered
        here.
        """
        # fmt: off
        query = """
            query PendingSteps {
                steps: agentPendingSteps {
                    %s
                }
            }
        """ % STEP_DISPATCH_FIELDS
        # fmt: on
        result = await self.execute(query)
        return cast(List[AgentStepDispatch], result.get("steps", []))

    async def claim_step(self, step_id: str) -> bool:
        """Atomically claim a dispatched step. False = already claimed."""
        # fmt: off
        mutate = """
            mutation ClaimStep($id: ID!) {
                claimed: claimPipelineStep(id: $id)
            }
        """
        # fmt: on
        result = await self.execute(mutate, params={"id": step_id})
        return bool(result.get("claimed"))

    async def complete_step(
        self,
        step_id: str,
        success: bool,
        output: Optional[dict] = None,
        rendered_input: Optional[dict] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Report the result of a claimed step."""
        # fmt: off
        mutate = """
            mutation CompleteStep($id: ID!, $input: CompletePipelineStepInput!) {
                completed: completePipelineStep(id: $id, input: $input)
            }
        """
        # fmt: on
        step_input = {"success": success}
        if output is not None:
            step_input["output"] = output
        if rendered_input is not None:
            step_input["renderedInput"] = rendered_input
        if error_message is not None:
            step_input["errorMessage"] = error_message
        result = await self.execute(
            mutate, params={"id": step_id, "input": step_input}
        )
        return bool(result.get("completed"))

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
        """Wrapper around execute"""
        removed_none = dict((k, v) for k, v in params.items() if v is not None)
        if type(query) == str:
            query = gql(query)
        return await self.session.execute(
            query, *args, variable_values=removed_none, **kwargs
        )
