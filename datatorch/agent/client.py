from datatorch.api import ApiClient


class AgentApiClient(ApiClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, use_sockets=True, **kwargs)
