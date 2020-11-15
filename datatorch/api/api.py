import logging, requests, os, cgi
from pathlib import Path

from typing import overload, cast
from urllib.parse import urlencode

from .client import Client

from .entity.file import File
from .entity.user import User
from .entity.project import Project
from .entity.settings import Settings as ApiSettings


__all__ = "ApiClient"


logger = logging.getLogger(__name__)


_SETTINGS = ApiSettings.add_fragment(
    """
    query GetSettings {
      settings {
        ...SettingsFields
      }
    }
    """
)

_PROJECT_BY_NAME = Project.add_fragment(
    """
    query GetProject($login: String!, $slug: String!) {
      project: project(login: $login, slug: $slug) {
        ...ProjectFields
      }
    }
    """
)

_PROJECT_BY_ID = Project.add_fragment(
    """
    query GetProjectId($id: ID!) {
      project: projectById(id: $id) {
        ...ProjectFields
      }
    }
    """
)

_FILE = File.add_fragment(
    """
    query GetFile($fileId: ID!) {
      file(id: $fileId) {
        ...FileFields
      }
    }
    """
)

_VIEWER = User.add_fragment(
    """
    query GetViewer {
      viewer {
        ...UserFields
      }
    }
    """
)


class ApiClient(Client):
    """ Adds simple queries to the client wrapper """

    def settings(self) -> ApiSettings:
        """ API instance settings """
        return cast(
            ApiSettings, self.query_to_class(ApiSettings, _SETTINGS, path="settings")
        )

    def viewer(self) -> User:
        """ Current logged in user """
        return cast(User, self.query_to_class(User, _VIEWER, path="viewer"))

    @overload
    def project(self, id: str) -> Project:  # type: ignore
        """ Retrieve a project by ID """
        pass

    @overload
    def project(self, login: str, slug: str) -> Project:  # type: ignore
        """ Retrieve a project by login and slug """
        pass

    def project(self, loginOrId: str, slug: str = None) -> Project:
        if slug:
            params = {"login": loginOrId, "slug": slug}
            query = _PROJECT_BY_NAME
        else:
            params = {"id": loginOrId}
            query = _PROJECT_BY_ID

        return cast(
            Project, self.query_to_class(Project, query, path="project", params=params)
        )

    def file(self, id: str) -> File:
        return cast(
            File, self.query_to_class(File, _FILE, path="file", params={"fileId": id})
        )

    def download_file(
        self,
        id: str,
        name: str = "",
        directory: str = "./",
    ):
        query_string = urlencode({"download": "true", "stream": "true"})
        download_url = f"{self.api_url}/file/v1/{id}/{name}?{query_string}"

        result = requests.get(
            download_url, headers={self.token_header: self._api_token}, stream=True
        )

        content = result.headers["content-disposition"]
        _, value = cgi.parse_header(content)

        name = name or value["filename"]
        name = os.path.join(directory, name)
        name = os.path.abspath(name)

        with open(name, "wb") as f:
            for chunk in result.iter_content(1024):
                f.write(chunk)

        return name, result

    # def files(self, where: Where = None, limit: int = 400) -> List[File]:
    #     return []

    def validate_endpoint(self) -> bool:
        """ Returns true if provided endpoint is correct. """
        try:
            version = self.settings().api_version
            logger.info("Endpoint API version: {}".format(version))
            return True
        except ConnectionRefusedError:
            return False
