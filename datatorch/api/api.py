import json
from typing import overload

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from datatorch.core.settings import Settings

from .settings import Settings as ApiSettings
from .project import Project
from .user import User


GET_API_SETTINGS = gql('''
    query GetSettings {
      settings {
        apiVersion
        api
        frontend
      }
    }
''')


GET_PROJECT_ID = gql('''
    query GetProjectId($id: ID!) {
      project: projectById(id: $id) {
        id
        slug
        name
        description
        visibility
        about
        ownerId
        namespace
        path
        pathWithSpaces
        avatarUrl
        isPrivate
        kilobytes
        formattedBytes
        isArchived
        createdAt
        updatedAt
      }
    }
''')


GET_PROJECT_SLUG = gql('''
    query GetProjectId($login: String!, $slug: String!) {
      project(login: $login, slug: $slug) {
        id
        slug
        name
        description
        visibility
        about
        ownerId
        namespace
        path
        pathWithSpaces
        avatarUrl
        isPrivate
        kilobytes
        formattedBytes
        isArchived
        createdAt
        updatedAt
      }
    }
''')


LOGIN = gql('''
    mutation Login($login: String!, $password: String!) {
      login(login: $login, password: $password) {
        token
        user {
          id
          login
          email
        }
      }
    }
''')


VIEWER = gql('''
    query {
      viewer {
        id
        name
        login
        email
        company
        location
        websiteUrl
        role
      }
    }
''')


class AuthenticationError(Exception):
    pass


class ApiClient(object):
    """ Wrapper for the DataTorch API including GraphQL and uploading """

    def __init__(self, api_key: str = None, api_url: str = None, settings: Settings = None):
        self._settings = settings or Settings()

        self.jwt: str = None
        self.api_key: str = api_key or self._settings.get('API_KEY')
        self.api_url: str = api_url or self._settings.get('API_URL')

        self.client = Client(
            transport=RequestsHTTPTransport(
                headers={'datatorch-api-key': self.api_key},
                use_json=True,
                url=self.graphql_url,
            ),
            fetch_schema_from_transport=True
        )

    @property
    def graphql_url(self):
        return '{}/graphql'.format(self.api_url)

    def login(self, login: str, password: str):
        params = {'login': login, 'password': password}
        results = self.execute(LOGIN, params=params)
        logged_in = results.get('login')
        token: str = logged_in.get('token')
        self.client.transport.headers['Authorization'] = f'Bearer {token}'
        return logged_in

    def logout(self):
        self.jwt = None

    def set_api_key(self, api_key: str = None):
        """ Update client API key. If value not provided get from users settings. """
        self.api_key = api_key or self._settings().get('API_KEY')
        self.client.transport.headers['datatorch-api-key'] = self.api_key

    def set_api_url(self, api_url=None):
        """ Update client API URL. If value not provided get from users settings. """
        self.api_url = api_url or self._settings().get('API_URL')
        self.client.transport.url = self.api_url

    def execute(self, *args, params: dict = {}, **kwargs):
        """ Wrapper around execute """
        params_json = json.dumps(params)
        return self.client.execute(*args, variable_values=params_json, **kwargs)

    def settings(self) -> ApiSettings:
        results = self.execute(GET_API_SETTINGS)
        return ApiSettings(self, results.get('settings'))

    @overload
    def project(self, id: str) -> Project:
        """ Retrieve a project by ID """
        pass

    @overload
    def project(self, login: str, slug: str) -> Project:
        """ Retrieve a project by login and slug """
        pass

    def viewer(self) -> User:
        results = self.execute(VIEWER)
        viewer = results.get('viewer')
        if viewer is None:
            raise AuthenticationError('API client is not logged in.')
        return User(self, results.get('viewer'))

    def project(self, loginOrId: str, slug: str = None) -> Project:
        if slug:
            params = {'login': loginOrId, 'slug': slug}
            results = self.execute(GET_PROJECT_SLUG, params=params)
        else:
            params = {'id': loginOrId}
            results = self.execute(GET_PROJECT_ID, params=params)

        return Project(self, results.get('project'))
