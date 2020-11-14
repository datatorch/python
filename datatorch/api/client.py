from typing import List, Union, cast

from gql import Client as GqlClient, gql
from gql.transport.transport import Transport
from gql.transport.websockets import WebsocketsTransport
from gql.transport.requests import RequestsHTTPTransport
from graphql.language.ast import DocumentNode

from datatorch.utils import normalize_api_url
from datatorch.core import user_settings
from typing import Any, TypeVar, Type


T = TypeVar("T")


__all__ = "Client"


_AGENT_TOKEN_HEADER = "datatorch-agent-token"
_API_KEY_HEADER = "datatorch-api-key"


class Client(object):
    """ Wrapper for the DataTorch API including GraphQL and uploading """

    @classmethod
    def create_socket_transport(
        cls, url: str, api_token: str = None, agent: bool = False
    ):
        return cast(
            WebsocketsTransport,
            cls.create_transport(url, api_token=api_token, agent=agent, sockets=True),
        )

    @staticmethod
    def create_transport(
        url: str, api_token: str = None, agent: bool = False, sockets: bool = False
    ):
        api_url = normalize_api_url(url)
        header_key = _AGENT_TOKEN_HEADER if agent else _API_KEY_HEADER
        headers = {header_key: api_token} if api_token else {}
        if sockets:
            api_url = api_url.replace("http", "ws", 1)
            return WebsocketsTransport(headers=headers, url=api_url)
        return RequestsHTTPTransport(headers=headers, use_json=True, url=api_url)

    def __init__(
        self,
        api_key: str = None,
        api_url: str = None,
        sockets: bool = False,
    ):
        self._use_sockets = sockets
        self._api_url = normalize_api_url(api_url or user_settings.api_url)
        self._graphql_url = f"{self.api_url}/graphql"
        self.transport = self.create_transport(self._graphql_url, sockets=sockets)
        self.client = GqlClient(
            transport=self.transport, fetch_schema_from_transport=True
        )
        self.set_api_key(api_key or user_settings.api_key)

    def set_api_key(self, api_key: str):
        headers = self.transport.headers
        if isinstance(headers, dict):
            headers[_API_KEY_HEADER] = api_key
            headers[_AGENT_TOKEN_HEADER] = None

    def set_agent_token(self, agent_token: str):
        self._api_key = agent_token
        headers = self.transport.headers
        if isinstance(headers, dict):
            headers[_API_KEY_HEADER] = None
            headers[_AGENT_TOKEN_HEADER] = agent_token

    @property
    def api_url(self) -> Union[str, None]:
        return self._api_url

    @property
    def graphql_url(self) -> str:
        return self.transport.url

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
        self, query: Union[DocumentNode, str], *args, params: dict = {}, **kwargs
    ) -> dict:
        """ Wrapper around execute """
        removed_none = dict((k, v) for k, v in params.items() if v is not None)
        query_doc = gql(query) if isinstance(query, str) else query
        return self.client.execute(
            query_doc, *args, variable_values=removed_none, **kwargs
        )

    def query_to_class(
        self, Entity: Type[T], query: str, path: str = "", params: dict = {}
    ) -> Union[T, List[T]]:
        results = self.execute(query, params=params)
        return self.to_class(Entity, results, path=path)

    def to_class(self, Entity, results: Union[dict, list, None], path: str = ""):

        for key in path.split("."):
            results = results.get(key)  # type: ignore

        if results is None:
            raise ValueError("Result value is null.")

        if type(results) == list:
            return list(map(lambda e: Entity(e, self), results))

        return Entity(results, self)
