from typing import AsyncGenerator, List, Optional, cast
from gql import gql
from .directory import runner_directory
from gql.client import AsyncClientSession
from gql.transport.exceptions import TransportError, TransportQueryError
from websockets.exceptions import ConnectionClosed

from typing_extensions import TypedDict
from asyncio import IncompleteReadError
import asyncio
import logging

logger = logging.getLogger(__name__)


class RunnerDisconnected(ConnectionError):
    """The runner has no live websocket session right now.

    `AgentApiClient.execute` raises it at once instead of sending into a
    dead transport. Callers whose message must get through (a finished
    step's result) wait on `AgentApiClient.wait_connected` and try again;
    callers that can afford to lose a message (a log batch, a metric) let
    it fail and send the next one.
    """


def is_transient(error: BaseException) -> bool:
    """Whether an API call failed because of the connection, so the same
    call may succeed once the runner is connected again.

    A `TransportQueryError` carrying GraphQL errors is the server's answer
    (the mutation was refused) and is not transient; the same class with
    no errors is gql's "query completed without any answer", which is the
    socket dropping mid-call.
    """
    if isinstance(error, TransportQueryError):
        return not error.errors
    return isinstance(
        error,
        (
            RunnerDisconnected,
            TransportError,
            ConnectionClosed,
            OSError,
            IncompleteReadError,
            asyncio.TimeoutError,
        ),
    )


class Log(TypedDict):
    createdAt: str
    message: str


class AgentStepDispatch(TypedDict):
    """A ready step pushed to this runner (runner protocol v2).

    ``input`` arrives server-resolved: ``steps.*`` and ``input.*``
    references are already substituted with concrete values.
    """

    stepId: str
    runnerId: str
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
    """A stop signal for a step this runner is currently running."""

    stepId: str
    runnerId: str


class AgentStepCancelRequest(TypedDict):
    cancel: AgentStepCancel


STEP_DISPATCH_FIELDS = """
    stepId
    runnerId
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
    """The runner's side of the runner wire protocol.

    One client lives as long as the daemon; the gql session behind it
    changes with every reconnect (`attach`/`detach`). While detached every
    call fails at once with `RunnerDisconnected`, so a step that finishes
    during an outage neither hangs on a dead socket nor reports into it.
    """

    def __init__(self, session: Optional[AsyncClientSession] = None):
        self.session = session
        self._connected = asyncio.Event()
        if session is not None:
            self._connected.set()

    @property
    def connected(self) -> bool:
        return self._connected.is_set()

    def attach(self, session: AsyncClientSession) -> None:
        """A (re)connected session: calls go through again."""
        self.session = session
        self._connected.set()

    def detach(self) -> None:
        """The connection is gone: refuse calls until the next `attach`."""
        self.session = None
        self._connected.clear()

    async def wait_connected(self, timeout: Optional[float] = None) -> bool:
        """Waits until a session is attached. False when `timeout` ran out."""
        try:
            await asyncio.wait_for(self._connected.wait(), timeout)
            return True
        except asyncio.TimeoutError:
            return False

    def agent_steps(self):
        """Subscribe to ready steps dispatched to this runner."""
        # fmt: off
        sub = gql("""
            subscription {
                step: runnerSteps {
                    %s
                }
            }
        """ % STEP_DISPATCH_FIELDS)
        # fmt: on
        return cast(AsyncGenerator[AgentStepRequest, None], self.session.subscribe(sub))

    def agent_step_cancels(self):
        """Subscribe to stop signals for steps this runner is running.

        Best effort: the server has already moved the step terminal, so a
        missed signal only means the step runs to harmless completion.
        """
        # fmt: off
        sub = gql("""
            subscription {
                cancel: runnerStepCancels {
                    stepId
                    runnerId
                }
            }
        """)
        # fmt: on
        return cast(
            AsyncGenerator[AgentStepCancelRequest, None],
            self.session.subscribe(sub),
        )

    async def pending_steps(self) -> List[AgentStepDispatch]:
        """Steps dispatched to this runner but not yet claimed.

        Called on (re)connect: pushes missed while offline are recovered
        here.
        """
        # fmt: off
        query = """
            query PendingSteps {
                steps: runnerPendingSteps {
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
        result = await self.execute(mutate, params={"id": step_id, "input": step_input})
        return bool(result.get("completed"))

    def runner_commands(self):
        """Subscribe to requests the server makes of this runner: read or
        write one of its own `actions/local/<name>/<tag>` folders (October
        2026). Answered with `complete_runner_command`."""
        # fmt: off
        sub = gql("""
            subscription {
                command: runnerCommands {
                    id
                    runnerId
                    kind
                    payload
                }
            }
        """)
        # fmt: on
        return self.session.subscribe(sub)

    def complete_runner_command(self, command_id: str, result=None, error: str = None):
        # fmt: off
        mutate = """
            mutation completeRunnerCommand($id: ID!, $result: JSON, $error: String) {
                completeRunnerCommand(id: $id, result: $result, error: $error)
            }
        """
        # fmt: on
        return self.execute(
            gql(mutate), params={"id": command_id, "result": result, "error": error}
        )

    def initial_metrics(self, metrics):
        # fmt: off
        mutate = """
            mutation updateRunner(
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
                updateRunner(id: $id, input: {
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
        params = {"id": runner_directory.settings.runner_id, **metrics}
        return self.execute(gql(mutate), params=params)

    def report_local_actions(self, actions):
        """Tells the server which `actions/local/<name>/<tag>` folders this
        runner holds (their action yaml text). The whole list each time: a
        folder no longer listed is gone from the server too."""
        # fmt: off
        mutate = """
            mutation reportRunnerLocalActions(
                $id: ID!
                $localActions: [RunnerLocalActionInput!]!
            ) {
                updateRunner(id: $id, input: { localActions: $localActions }) {
                    id
                }
            }
        """
        # fmt: on
        params = {"id": runner_directory.settings.runner_id, "localActions": actions}
        return self.execute(gql(mutate), params=params)

    def metrics(self, metrics):
        # fmt: off
        mutate = """
            mutation createRunnerMetric(
                $runnerId: ID!
                $sampledAt: DateTime!
                $avgLoad1: Float
                $avgLoad5: Float
                $avgLoad15: Float
                $cpuUsage: Float
                $diskUsage: Float
                $memoryUsage: Float
            ) {
                createRunnerMetric(input: {
                    runnerId: $runnerId
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
        params = {"runnerId": runner_directory.settings.runner_id, **metrics}
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

    async def force_reconnect(self) -> None:
        """Closes the websocket so the steps subscription raises and the
        outer loop in `agent.start()` reconnects with backoff."""
        transport = getattr(self.session, "transport", None)
        if transport is None or getattr(transport, "websocket", None) is None:
            return
        try:
            await transport.close()
        except Exception as e:
            logger.debug(f"Transport close raised while forcing reconnect: {e}")

    async def execute(self, query, *args, params: dict = {}, **kwargs) -> dict:
        """Wrapper around execute. Raises `RunnerDisconnected` while no
        session is attached (see the class docstring)."""
        session = self.session
        if session is None or not self._connected.is_set():
            raise RunnerDisconnected("The runner is not connected to DataTorch.")
        removed_none = dict((k, v) for k, v in params.items() if v is not None)
        if type(query) == str:
            query = gql(query)
        return await session.execute(
            query, *args, variable_values=removed_none, **kwargs
        )
