import logging

from ..step import Step
from ..template import Variables
from ..resolver import UnresolvedReferenceError, resolve_step_input

logger = logging.getLogger("datatorch.agent.job")


class Job(object):
    """
    LOCAL-MODE step sequencer (``datatorch pipeline run <yaml>``).

    Against the server, jobs are sequenced by the server-side orchestrator
    and this class is not involved — the agent executes one dispatched
    step at a time. Local mode replicates the server's behavior so the
    same yaml works in both places: steps run sequentially, each step's
    ``${{ steps.<name>.output.<key> }}`` / ``${{ input.<key> }}``
    references are resolved (strictly) from earlier outputs before it
    runs, and the first failure skips the rest.
    """

    def __init__(self, config: dict, trigger_input: dict = None):
        self.config = config
        self.name = config.get("name")
        self.trigger_input = trigger_input or {}

    async def run(self):
        """Runs each step of the job, resolving references in between."""
        outputs_by_name = {}

        for step_config in self.config.get("steps", []):
            name = step_config.get("name")
            try:
                resolved, unresolved = resolve_step_input(
                    step_config.get("inputs", {}),
                    outputs_by_name,
                    self.trigger_input,
                )
                if unresolved:
                    raise UnresolvedReferenceError(unresolved)

                step = Step.from_dict({**step_config, "inputs": resolved})
                outputs = await step.run(Variables())
                if name:
                    outputs_by_name[name] = outputs or {}
            except Exception as e:
                logger.error(f"Job {self.name} failed on step '{name}': {e}")
                logger.error("Skipping remaining steps.")
                raise

        logger.info(f"Successfully completed job '{self.name}'.")
        return outputs_by_name
