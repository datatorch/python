from gql import gql
from datatorch.api import ApiClient


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

    async def metrics(self):
        pass

    async def random(self):
        pass
