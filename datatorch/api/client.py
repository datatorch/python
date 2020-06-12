import json

from typing import List, Union

from gql import Client as GqlClient, gql
from gql.transport.requests import RequestsHTTPTransport

from datatorch.core.settings import Settings


__all__ = "Client"


class Client(object):
    """ Wrapper for the DataTorch API including GraphQL and uploading """

    def __init__(
        self, api_key: str = None, api_url: str = None, settings: Settings = None
    ):
        self._settings = settings or Settings()

        self.client = GqlClient(
            transport=RequestsHTTPTransport(
                headers={}, use_json=True, url=f"{api_url}/graphql" or self.api_url
            ),
            fetch_schema_from_transport=True,
        )

        self.api_key = api_key
        self.api_url = api_url

    @property
    def api_key(self) -> str:
        return self._api_key or self._settings.get("API_KEY")

    @api_key.setter
    def api_key(self, api_key):
        self._api_key = api_key
        self.client.transport.headers["datatorch-api-key"] = self.api_key

    @property
    def api_url(self) -> str:
        return self._api_url or self._settings.get("API_URL")

    @api_url.setter
    def api_url(self, value):
        self._api_url = value
        self.client.transport.url = self.graphql_url

    @property
    def graphql_url(self) -> str:
        return "{}/graphql".format(self.api_url)

    def execute_files(
        self, paths: List[str], *args, params: dict = {}, **kwargs
    ) -> dict:
        """ Combine and excute query of multiple GraphQL files """
        query = ""
        for path in paths:
            with open(path) as f:
                query += f.read()
        return self.execute(query, *args, params=params, **kwargs)

    def execute_file(self, path: str, *args, params: dict = {}, **kwargs) -> dict:
        """ Excute query from GraphQL file """
        with open(path) as f:
            return self.execute(f.read(), *args, params=params, **kwargs)

    def execute(
        self, query: Union[any, str], *args, params: dict = {}, **kwargs
    ) -> dict:
        """ Wrapper around execute """
        removed_none = dict((k, v) for k, v in params.items() if v is not None)
        params_json = json.dumps(removed_none)
        if type(query) == str:
            query = gql(query)
        return self.client.execute(query, *args, variable_values=params_json, **kwargs)

    def query_to_class(self, Entity, query: str, path: str = "", params: dict = {}):
        results = self.execute(query, params=params)
        return self.to_class(Entity, results, path=path)

    def to_class(self, Entity, results: dict, path: str = ""):

        for key in path.split("."):
            results = results.get(key)

        if results is None:
            raise ValueError("Result value is null.")

        if type(results) == list:
            return list(map(lambda e: Entity(e, self), results))

        return Entity(results, self)
