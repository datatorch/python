# Edit this to set custom variables
RUNNER_ID = "DATATORCH_RUNNER_ID"
# The pre-October-2026 spelling, still honored.
AGENT_ID = "DATATORCH_AGENT_ID"
API_KEY = "DATATORCH_API_KEY"
# A runner hands its own token to the actions it runs (October 2026).
RUNNER_TOKEN = "DATATORCH_RUNNER_TOKEN"
API_URL = "DATATORCH_API_URL"
CONFIG_DIR = "DATATORCH_DIR"
# The step's place in the record, handed to every action a runner runs
# (0.8.1): the project the run belongs to, the run, the pipeline and the
# step. An action that works "for this project" reads PROJECT_ID instead
# of carrying a project input, so a pipeline forked into another project
# works there unchanged.
PROJECT_ID = "DATATORCH_PROJECT_ID"
RUN_ID = "DATATORCH_RUN_ID"
PIPELINE_ID = "DATATORCH_PIPELINE_ID"
STEP_ID = "DATATORCH_STEP_ID"
