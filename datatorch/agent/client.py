from gql import gql
from datatorch.api import ApiClient
from .directory import agent_directory


class AgentApiClient(ApiClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, use_sockets=True, **kwargs)

    def agent_jobs(self):
        """ Subscriptions to the agent job assignment namespace. """
        # fmt: off
        sub = gql("""
            subscription {
                createJob {
                    id
                }
            }
        """)
        # fmt: on
        return self.client.subscribe_async(sub)

    async def step_logs(self):
        """ Sends logs produced from a step to the server. """
        pass

    def initial_metrics(self, metrics):
        # fmt: off
        mutate = """
            mutation updateAgent(
                $id: ID!
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

    def metrics(self):
        pass
