import os
import tempfile

# Isolate the agent directory BEFORE any datatorch module is imported —
# datatorch.runner.directory materializes `runner_directory` (and creates
# its folder tree) at import time. Without this, tests would read/write
# the developer's real ~/.datatorch/agent.
os.environ.setdefault(
    "DATATORCH_RUNNER_PATH",
    os.path.join(tempfile.mkdtemp(prefix="datatorch-test-"), "agent"),
)
