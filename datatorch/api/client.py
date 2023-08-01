from typing import List, Union, cast, IO
import requests, glob, os, cgi
from urllib.parse import urlencode

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


AGENT_TOKEN_HEADER = "datatorch-agent-token"
API_KEY_HEADER = "datatorch-api-key"


def _get_token_header(agent: bool = False):
    return AGENT_TOKEN_HEADER if agent else API_KEY_HEADER


class Client(object):
    """Wrapper for the DataTorch API including GraphQL and uploading"""

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
        graphql_url = f"{normalize_api_url(url)}/graphql"
        header_key = _get_token_header(agent)
        headers = {header_key: api_token} if api_token else {}
        if sockets:
            graphql_url = graphql_url.replace("http", "ws", 1)
            return WebsocketsTransport(headers=headers, url=graphql_url)
        return RequestsHTTPTransport(headers=headers, use_json=True, url=graphql_url)

    def __init__(
        self,
        api_key: str = None,
        api_url: str = None,
        sockets: bool = False,
        agent: bool = False,
    ):
        self._use_sockets = sockets
        self._is_agent = agent

        self._api_token = api_key or user_settings.api_url
        # This is to fix init bugs
        if api_url is None and user_settings.api_url is None:
            self._api_url = "https://datatorch.io/api"
        if not api_url is None:
            self._api_url = normalize_api_url(api_url)
        if not user_settings.api_url is None:
            self._api_url = normalize_api_url(user_settings.api_url)

        self._graphql_url = f"{self.api_url}/graphql"

        self.transport = self.create_transport(
            self._api_url, sockets=sockets, agent=agent
        )
        self.client = GqlClient(
            transport=self.transport, fetch_schema_from_transport=True
        )
        self.set_api_token(api_key or user_settings.api_key)

    @property
    def token_header(self):
        return AGENT_TOKEN_HEADER if self._is_agent else API_KEY_HEADER

    def set_api_token(self, api_key: str):
        headers = self.transport.headers
        self._api_token = api_key
        if isinstance(headers, dict):
            headers[self.token_header] = api_key

    @property
    def api_url(self) -> str:
        return self._api_url

    @property
    def graphql_url(self) -> str:
        return self._graphql_url

    @property
    def graphql_url(self) -> str:
        return self.transport.url

    def execute_files(
        self, paths: List[str], *args, params: dict = {}, **kwargs
    ) -> dict:
        """Combine and excute query of multiple GraphQL files"""
        query = ""
        for path in paths:
            with open(path) as f:
                query += f.read()
        return self.execute(query, *args, params=params, **kwargs)

    def execute_file(self, path: str, *args, params: dict = {}, **kwargs) -> dict:
        """Excute query from GraphQL file"""
        with open(path) as f:
            return self.execute(f.read(), *args, params=params, **kwargs)

    def execute(
        self, query: Union[DocumentNode, str], *args, params: dict = {}, **kwargs
    ) -> dict:
        """Wrapper around execute"""
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

    def download_file(
        self,
        id: str,
        name: str = "",
        directory: str = "./",
        skip: bool = True
        # For now, skip does nothing
    ):
        ## If it exists and skip is true, do not download
        # name = os.path.join(directory, name)
        # name = os.path.abspath(name)
        # This name overwrites the value into name
        # Causes a problem on line 175 if name is expected to be empty
        # On first run of download file name is supposed to ''
        # Loaded as default value from action-datatorch.yaml
        # But on subsequent runs if file exists, name is not empty
        # Temporary fix here
        dl_file = os.path.join(directory, name)
        dl_file = os.path.abspath(dl_file)

        if os.path.isfile(dl_file) & skip == True:
            return dl_file, None

        query_string = urlencode({"download": "true", "stream": "true"})
        url = normalize_api_url(self.api_url)
        download_url = f"{url}/file/v1/{id}/{name}?{query_string}"

        result = requests.get(
            download_url, headers={self.token_header: self._api_token}, stream=True
        )

        content = result.headers["content-disposition"]
        _, value = cgi.parse_header(content)

        name = name or value["filename"]
        name = os.path.join(directory, name)
        name = os.path.abspath(name)

        os.makedirs(os.path.dirname(name), exist_ok=True)

        with open(name, "wb") as f:
            for chunk in result.iter_content(1024):
                f.write(chunk)

        return name, result
