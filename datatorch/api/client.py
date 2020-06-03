import os

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from datatorch.core import env
from datatorch.core.settings import Settings


class DataTorchClient(object):
    def __init__(self):
        self._settings = Settings()
        self.client = Client(
            transport=RequestsHTTPTransport(
                url=self.host_url,
                auth=self.api_key
            )
        )

    @property
    def host_url(self):
        return os.getenv(env.HOST_URL)

    @property
    def api_key(self):
        return os.getenv(env.API_KEY) or ''

    def set_api_key(self):
        self.client.transport.auth = self.api_key

    def set_host_url(self):
        self.client.transport.url = self.host_url

    def excute(self, *args, **kwargs):
        """ Wrapper around excute """
        return self.client.execute(*args, **kwargs)

    def file_upload(self):
        pass
