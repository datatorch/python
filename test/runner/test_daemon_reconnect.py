"""
Runner daemon across a lost websocket (0.8.3).

A transport failure used to cancel every running step (the prod runner
lost a seed step 46 seconds in to a four-second blip on 2026-11-09). Now
the daemon outlives the connection: steps keep running, a step that
finishes while disconnected holds its result until the next session and
reports it then, finished tasks leave the task list, and only a real
shutdown cancels steps.

No network: a scripted fake gql client/session stands in for the
transport, and a fake Step stands in for the action.
"""

import asyncio
import logging

import pytest
from graphql import print_ast
from websockets.exceptions import ConnectionClosedError

import datatorch.runner as runner
import datatorch.runner.daemon as daemon_module
from datatorch.runner.client import RunnerDisconnected, is_transient
from datatorch.runner.daemon import RunnerDaemon, tasks
from gql.transport.exceptions import TransportQueryError

DISPATCH = {
    "stepId": "step-1",
    "runnerId": "runner-1",
    "action": "local/sleep@v1",
    "stepName": "sleep",
    "stepIndex": 0,
    "input": {},
    "jobId": "job-1",
    "jobName": "main",
    "runId": "run-1",
    "runNumber": 12,
    "pipelineId": "pipe-1",
    "projectId": "proj-1",
}


class FakeStep:
    """Stands in for `Step`: runs until the test lets it finish."""

    instances = []

    def __init__(self, dispatch, api):
        self.id = dispatch.get("stepId")
        self.api = api
        self.rendered_inputs = {"seconds": 1}
        self.logs = [{"createdAt": "2026-11-09T14:39:00Z", "message": "working"}]
        self.finish = asyncio.Event()
        self.cancelled = False
        self.fail_with = None
        FakeStep.instances.append(self)

    @classmethod
    def from_dispatch(cls, dispatch, api=None):
        return cls(dispatch, api)

    async def run(self, variables):
        try:
            await self.finish.wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        if self.fail_with:
            raise self.fail_with
        return {"result": "done"}

    def log(self, message):
        self.logs.append({"createdAt": "2026-11-09T14:40:00Z", "message": message})

    async def upload_logs(self):
        if self.api and self.logs:
            logs, self.logs = self.logs, []
            try:
                await self.api.upload_step_logs(self.id, logs)
            except BaseException:
                self.logs = logs + self.logs
                raise


class FakeSession:
    """One connection: answers the runner protocol from a script.

    `steps` is an async generator factory for the runnerSteps subscription;
    the other subscriptions block until cancelled. Mutations are recorded
    in `calls`. `drop` makes every call fail like a dead socket.
    """

    def __init__(self, steps, complete_result=True):
        self.steps = steps
        self.complete_result = complete_result
        self.calls = []
        self.dropped = False

    async def execute(self, document, variable_values=None, **kwargs):
        text = print_ast(document)
        if self.dropped:
            raise TransportQueryError(
                "Query completed without any answer received from the server"
            )
        if "runnerPendingSteps" in text:
            return {"steps": []}
        if "claimPipelineStep" in text:
            self.calls.append(("claim", variable_values))
            return {"claimed": True}
        if "completePipelineStep" in text:
            self.calls.append(("complete", variable_values))
            return {"completed": self.complete_result}
        if "createPipelineStepLog" in text:
            self.calls.append(("logs", variable_values))
            return {"createPipelineStepLog": True}
        # updateRunner / createRunnerMetric
        return {"updateRunner": {"id": "runner-1"}, "createRunnerMetric": {"id": "m"}}

    def subscribe(self, document, **kwargs):
        text = print_ast(document)
        if "runnerSteps" in text:
            return self.steps()
        return self._block_forever()

    async def _block_forever(self):
        await asyncio.Event().wait()
        yield  # pragma: no cover


class FakeClient:
    """`async with client as session` hands out the scripted sessions in
    order; the last one is reused if the loop reconnects again."""

    def __init__(self, sessions, reconnect_gate=None):
        self.sessions = list(sessions)
        self.connections = 0
        self.connected = asyncio.Event()
        # When set, every connection after the first waits for this event.
        self.reconnect_gate = reconnect_gate

    async def __aenter__(self):
        if self.reconnect_gate is not None and self.connections >= 1:
            await self.reconnect_gate.wait()
        index = min(self.connections, len(self.sessions) - 1)
        self.connections += 1
        self.connected.set()
        return self.sessions[index]

    async def __aexit__(self, exc_type, exc, tb):
        self.connected.clear()
        return False


class FakeTransport:
    close_task = None
    websocket = None


def _dispatch_then_drop(drop: asyncio.Event, session_holder: dict):
    """runnerSteps script: push one step, then fail like a lost socket."""

    async def steps():
        yield {"step": dict(DISPATCH)}
        await drop.wait()
        session_holder["session"].dropped = True
        raise ConnectionClosedError(None, None)

    return steps


def _idle():
    async def steps():
        await asyncio.Event().wait()
        yield  # pragma: no cover

    return steps


@pytest.fixture(autouse=True)
def fast_loop(monkeypatch):
    """No real backoff or deadlines in tests; fake Step; clean task list."""
    monkeypatch.setattr(runner, "BACKOFF_INIT_WAIT", 0.01)
    monkeypatch.setattr(runner, "BACKOFF_MAX", 0.01)
    monkeypatch.setattr(daemon_module, "REPORT_RETRY_SECONDS", 0.01)
    monkeypatch.setattr(daemon_module, "Step", FakeStep)
    FakeStep.instances = []
    tasks.clear()
    yield
    tasks.clear()


async def _until(predicate, timeout=5):
    async def wait():
        while not predicate():
            await asyncio.sleep(0.005)

    await asyncio.wait_for(wait(), timeout)


def test_step_survives_a_dropped_connection_and_reports_after_reconnect(caplog):
    async def inner():
        drop = asyncio.Event()
        holder = {}
        first = FakeSession(_dispatch_then_drop(drop, holder))
        holder["session"] = first
        second = FakeSession(_idle())
        client = FakeClient([first, second])
        daemon = RunnerDaemon()

        loop_task = asyncio.ensure_future(
            runner.serve_forever(client, FakeTransport(), daemon)
        )

        # The step is dispatched, claimed and running on connection 1.
        await _until(lambda: FakeStep.instances)
        step = FakeStep.instances[0]
        await _until(lambda: ("claim", {"id": "step-1"}) in first.calls)
        assert len(daemon.running_steps()) == 1

        # The socket dies mid-step.
        drop.set()
        await _until(lambda: client.connections >= 2)

        # The step task is still running, untouched by the reconnect.
        assert not step.cancelled
        assert len(daemon.running_steps()) == 1
        assert first.calls.count(("complete", {"id": "step-1"})) == 0

        # It finishes on the new connection and reports there.
        step.finish.set()
        await _until(lambda: any(c[0] == "complete" for c in second.calls))
        kinds = [c[0] for c in second.calls]
        assert kinds.index("logs") < kinds.index("complete")  # logs first
        complete = next(c for c in second.calls if c[0] == "complete")
        assert complete[1]["input"]["success"] is True
        assert complete[1]["input"]["output"] == {"result": "done"}
        assert complete[1]["input"]["renderedInput"] == {"seconds": 1}
        assert not any(c[0] == "complete" for c in first.calls)

        # The finished task left the registries.
        await _until(lambda: not daemon.running_steps())
        assert not any(t.done() for t in tasks)

        # A cancel is a shutdown: the loop ends quietly.
        loop_task.cancel()
        await loop_task

    asyncio.run(asyncio.wait_for(inner(), timeout=10))


def test_step_finishing_while_disconnected_waits_for_the_next_session():
    async def inner():
        drop = asyncio.Event()
        holder = {}
        first = FakeSession(_dispatch_then_drop(drop, holder))
        holder["session"] = first
        second = FakeSession(_idle())
        # Hold the reconnect: the loop may not reach connection 2 until we say.
        gate = asyncio.Event()
        client = FakeClient([first, second], reconnect_gate=gate)
        daemon = RunnerDaemon()

        loop_task = asyncio.ensure_future(
            runner.serve_forever(client, FakeTransport(), daemon)
        )
        await _until(lambda: FakeStep.instances)
        step = FakeStep.instances[0]
        await _until(lambda: ("claim", {"id": "step-1"}) in first.calls)

        drop.set()
        await _until(lambda: not daemon.api.connected)

        # Finishes while offline: nothing is sent into the dead session,
        # the task stays alive holding the result.
        step.finish.set()
        await asyncio.sleep(0.05)
        assert not any(c[0] == "complete" for c in first.calls)
        assert len(daemon.running_steps()) == 1

        gate.set()
        await _until(lambda: any(c[0] == "complete" for c in second.calls))
        await _until(lambda: not daemon.running_steps())

        # A cancel is a shutdown: the loop ends quietly.
        loop_task.cancel()
        await loop_task

    asyncio.run(asyncio.wait_for(inner(), timeout=10))


def test_result_is_dropped_after_the_report_deadline(monkeypatch, caplog):
    monkeypatch.setattr(daemon_module, "REPORT_DEADLINE_SECONDS", 0.1)
    caplog.set_level(logging.WARNING, logger="datatorch.runner.daemon")

    async def inner():
        daemon = RunnerDaemon()  # never connected
        daemon._start_step(dict(DISPATCH))
        # The claim fails at once (disconnected): the step is not run and
        # will be offered again on reconnect.
        await _until(lambda: not daemon.running_steps())
        assert FakeStep.instances == []

        # A step that finished during an outage that never ends.
        daemon.api.attach(FakeSession(_idle()))
        daemon._start_step(dict(DISPATCH))
        await _until(lambda: FakeStep.instances)
        step = FakeStep.instances[0]
        daemon.api.detach()
        step.finish.set()
        task = daemon._step_tasks["step-1"]
        await asyncio.wait_for(task, timeout=5)
        assert task.exception() is None
        assert not daemon.running_steps()

    asyncio.run(asyncio.wait_for(inner(), timeout=10))
    assert "could not report its result" in caplog.text


def test_late_completion_refused_by_the_server_is_absorbed(caplog):
    caplog.set_level(logging.WARNING, logger="datatorch.runner.daemon")

    async def inner():
        session = FakeSession(_idle(), complete_result=False)
        daemon = RunnerDaemon()
        daemon.api.attach(session)
        daemon._start_step(dict(DISPATCH))
        await _until(lambda: FakeStep.instances)
        FakeStep.instances[0].finish.set()
        task = daemon._step_tasks["step-1"]
        await asyncio.wait_for(task, timeout=5)
        assert task.exception() is None
        assert any(c[0] == "complete" for c in session.calls)

    asyncio.run(asyncio.wait_for(inner(), timeout=10))
    assert "did not accept the result" in caplog.text


def test_failed_step_reports_failure_across_a_retry():
    async def inner():
        session = FakeSession(_idle())
        daemon = RunnerDaemon()
        daemon.api.attach(session)
        daemon._start_step(dict(DISPATCH))
        await _until(lambda: FakeStep.instances)
        step = FakeStep.instances[0]
        step.fail_with = RuntimeError("boom")

        # The first completion attempt dies on the wire; the second lands.
        real_execute = session.execute
        failures = {"left": 1}

        async def flaky(document, variable_values=None, **kwargs):
            if "completePipelineStep" in print_ast(document) and failures["left"]:
                failures["left"] -= 1
                raise RunnerDisconnected("blip")
            return await real_execute(document, variable_values, **kwargs)

        session.execute = flaky
        step.finish.set()
        await asyncio.wait_for(daemon._step_tasks["step-1"], timeout=5)
        complete = [c for c in session.calls if c[0] == "complete"]
        assert len(complete) == 1
        assert complete[0][1]["input"] == {
            "success": False,
            "errorMessage": "boom",
        }

    asyncio.run(asyncio.wait_for(inner(), timeout=10))


def test_shutdown_still_cancels_running_steps():
    async def inner():
        session = FakeSession(_idle())
        daemon = RunnerDaemon()
        daemon.api.attach(session)
        daemon._start_step(dict(DISPATCH))
        await _until(lambda: FakeStep.instances)
        step = FakeStep.instances[0]
        assert len(daemon.running_steps()) == 1

        runner._daemon = daemon
        try:
            await runner._exit_jobs()
        finally:
            runner._daemon = None

        assert step.cancelled
        assert not daemon.running_steps()
        assert not any(c[0] == "complete" for c in session.calls)
        assert tasks == []

    asyncio.run(asyncio.wait_for(inner(), timeout=10))


def test_duplicate_dispatch_for_a_running_step_is_ignored():
    async def inner():
        session = FakeSession(_idle())
        daemon = RunnerDaemon()
        daemon.api.attach(session)
        daemon._start_step(dict(DISPATCH))
        await _until(lambda: FakeStep.instances)
        daemon._start_step(dict(DISPATCH))
        await asyncio.sleep(0.02)
        assert len(FakeStep.instances) == 1
        assert len(daemon.running_steps()) == 1
        FakeStep.instances[0].finish.set()
        await _until(lambda: not daemon.running_steps())

    asyncio.run(asyncio.wait_for(inner(), timeout=10))


def test_is_transient_tells_a_dead_socket_from_a_refusal():
    assert is_transient(RunnerDisconnected("x"))
    assert is_transient(ConnectionClosedError(None, None))
    assert is_transient(OSError("reset"))
    assert is_transient(asyncio.TimeoutError())
    assert is_transient(TransportQueryError("no answer"))
    assert not is_transient(
        TransportQueryError("Not authorized", errors=[{"message": "Not authorized"}])
    )
    assert not is_transient(RuntimeError("bug"))
