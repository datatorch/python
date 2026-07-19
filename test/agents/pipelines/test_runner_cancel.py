"""
Agent-side cancel (Phase 7): when the asyncio task running a step is
cancelled — the server pushed a stop signal, or the agent disconnected —
the runner must kill its child process instead of orphaning it, and let the
CancelledError propagate so the step aborts.
"""
import asyncio

import pytest

from datatorch.agent.pipelines.runner.runner import Runner


class _FakeAction:
    step = None
    dir = "."


def test_monitor_cmd_kills_child_on_cancel():
    async def inner():
        runner = Runner({}, _FakeAction())

        # Capture the spawned process so we can assert it was killed.
        captured = {}
        original = runner.run_cmd

        async def capturing(command, wait=True, env=None):
            proc = await original(command, wait=wait, env=env)
            captured["proc"] = proc
            return proc

        runner.run_cmd = capturing

        # `sleep 30` produces no stdout, so monitor_cmd blocks reading it.
        task = asyncio.ensure_future(runner.monitor_cmd("sleep 30"))
        await asyncio.sleep(0.3)  # let the child actually start
        assert captured["proc"].returncode is None  # running

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        # The child was killed (returncode set), not left running.
        assert captured["proc"].returncode is not None

    # A short wall-clock timeout guards against a regression where cancel
    # hangs waiting for the full `sleep 30`.
    asyncio.run(asyncio.wait_for(inner(), timeout=10))
