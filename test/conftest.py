import os
import tempfile

# Isolate the agent directory BEFORE any datatorch module is imported —
# datatorch.agent.directory materializes `agent_directory` (and creates
# its folder tree) at import time. Without this, tests would read/write
# the developer's real ~/.datatorch/agent.
os.environ.setdefault(
    "DATATORCH_AGENT_PATH",
    os.path.join(tempfile.mkdtemp(prefix="datatorch-test-"), "agent"),
)
