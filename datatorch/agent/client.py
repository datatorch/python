from gql import gql
from .directory import agent_directory


class AgentApiClient(object):
    def __init__(self, session):
        self.session = session

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
        return self.session.subscribe(sub)

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

    def execute(self, query, *args, params: dict = {}, **kwargs) -> dict:
        """ Wrapper around execute """
        removed_none = dict((k, v) for k, v in params.items() if v is not None)
        if type(query) == str:
            query = gql(query)
        return self.session.execute(
            query, *args, variable_values=removed_none, **kwargs
        )
