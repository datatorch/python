"""
Agent-side cancel (Phase 7): when the asyncio task running a step is
cancelled — the server pushed a stop signal, or the agent disconnected —
the runner must kill its child process instead of orphaning it, and let the
CancelledError propagate so the step aborts.
"""

import asyncio
import os
import shlex
import sys
import time

import psutil
import pytest

from datatorch.runner.pipelines.runner import runner as runner_module
from datatorch.runner.pipelines.runner.runner import Runner


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


# --- The whole tree stops, not only the shell (0.8.4) -----------------------
#
# On 2026-11-11 a seed step hit its timeout, the runner killed the shell that
# wrapped the action, and the `claude` process under it kept working against
# the server for another 40 minutes. The test above could not see that: it
# only looked at the shell's own return code.


def _gone(pid: int) -> bool:
    try:
        proc = psutil.Process(pid)
        return proc.status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return True


def _cancel_and_collect(command: str, pid_file: str, expected: int = 1):
    """Run `command` as a step, wait until it has written `expected` pids
    to `pid_file`, cancel the step, and return those pids."""

    async def inner():
        runner = Runner({}, _FakeAction())
        task = asyncio.ensure_future(runner.monitor_cmd(command))

        pids = []
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and len(pids) < expected:
            await asyncio.sleep(0.05)
            if os.path.exists(pid_file):
                with open(pid_file) as handle:
                    pids = [int(part) for part in handle.read().split()]
        assert len(pids) == expected, "the step never started its children"
        assert all(psutil.pid_exists(pid) for pid in pids)

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return pids

    return asyncio.run(asyncio.wait_for(inner(), timeout=20))


@pytest.mark.skipif(os.name != "posix", reason="process groups are POSIX")
def test_cancel_stops_a_grandchild(tmp_path):
    """The shape of a python action: the shell starts a program, and that
    program starts another. Both must be gone after a cancel."""
    pid_file = str(tmp_path / "pids")
    command = f"(sleep 60 & echo $! > {shlex.quote(pid_file)}; wait)"

    (grandchild,) = _cancel_and_collect(command, pid_file)

    assert _gone(grandchild)


@pytest.mark.skipif(os.name != "posix", reason="sessions are POSIX")
def test_cancel_stops_a_grandchild_in_its_own_session(tmp_path):
    """A program that puts its children in their own session (an agent's
    shell tool does) takes them out of the step's process group. They are
    still found, by parentage, and stopped."""
    pid_file = str(tmp_path / "pids")
    script = (
        "import subprocess, sys;"
        "p = subprocess.Popen(['sleep', '60'], start_new_session=True);"
        "open(sys.argv[1], 'w').write(str(p.pid));"
        "p.wait()"
    )
    command = " ".join(
        shlex.quote(part) for part in (sys.executable, "-c", script, pid_file)
    )

    (grandchild,) = _cancel_and_collect(command, pid_file)

    assert _gone(grandchild)


@pytest.mark.skipif(os.name != "posix", reason="signals are POSIX")
def test_cancel_kills_what_ignores_the_polite_stop(tmp_path, monkeypatch):
    """A process that ignores SIGTERM is killed once the grace runs out."""
    monkeypatch.setattr(runner_module, "TERMINATE_GRACE_SECONDS", 0.5)
    pid_file = str(tmp_path / "pids")
    command = f"trap '' TERM; (sleep 60 & echo $! > {shlex.quote(pid_file)}; wait)"

    started = time.monotonic()
    (grandchild,) = _cancel_and_collect(command, pid_file)

    assert _gone(grandchild)
    assert time.monotonic() - started < 10


@pytest.mark.skipif(os.name != "posix", reason="process groups are POSIX")
def test_a_step_runs_outside_the_runners_process_group():
    """The stop signals a whole group, so that group must never be the
    runner's own."""

    async def inner():
        runner = Runner({}, _FakeAction())
        process = await runner.run_cmd("sleep 60", wait=False)
        try:
            assert os.getpgid(process.pid) == process.pid
            assert os.getpgid(process.pid) != os.getpgrp()
        finally:
            await runner._terminate(process)
        assert process.returncode is not None

    asyncio.run(asyncio.wait_for(inner(), timeout=10))
