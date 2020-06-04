import os
import json
import logging

from typing import overload

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from datatorch.core import env, settings
from datatorch.core.settings import Settings

from .settings import Settings as ApiSettings
from .project import Project


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


class ApiClient(object):
    """ Wrapper for the DataTorch API including GraphQL and uploading """

    def __init__(self, api_key: str = None, api_url: str = None):
        self._settings = Settings()

        self.api_key: str = api_key or settings.get('API_KEY')
        self.api_url: str = api_url or settings.get('API_URL')

        self.client = Client(
            transport=RequestsHTTPTransport(
                use_json=True,
                url=self.graphql_url,
            ),
            fetch_schema_from_transport=True
        )

    @property
    def graphql_url(self):
        return '{}/graphql'.format(self.api_url)

    def set_api_key(self, api_key: str = None):
        """ Update client API key. If value not provided get from users settings. """
        self.api_key = api_key or self._settings().get('API_KEY')
        self.client.transport.auth = self.api_key

    def set_api_url(self, api_url=None):
        """ Update client API URL. If value not provided get from users settings. """
        self.api_url = api_url or self._settings().get('API_URL')
        self.client.transport.url = api_key or self.api_url

    def execute(self, *args, **kwargs):
        """ Wrapper around execute """
        return self.client.execute(*args, **kwargs)

    def settings(self) -> ApiSettings:
        results = self.execute(GET_API_SETTINGS)
        return ApiSettings(self, results.get('settings'))

    @overload
    def project(self, id: str) -> Project:
        """ Retrieve a project by ID """
        pass

    @overload
    def project(self, login: str, slug: str) -> Project:
        """ Retrieve a project by namespace and slug """
        pass

    def project(self, loginOrId: str, slug: str = None) -> Project:
        if slug:
            params = json.dump({'login': loginOrId, 'slug': slug})
            results = self.execute(
                GET_PROJECT_SLUG, varsvariable_values=params)
        else:
            params = json.dumps({'id': loginOrId})
            results = self.execute(GET_PROJECT_ID, variable_values=params)

        return Project(self, results.get('project'))
