import logging, os, requests, glob

from typing import IO, overload, cast

try:
    import magic
except ImportError:
    magic = None
    import mimetypes

from datatorch.api.entity.dataset import Dataset
from datatorch.api.entity.storage_link import StorageLink
from datatorch.utils import normalize_api_url
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
    """Adds simple queries to the client wrapper"""

    def settings(self) -> ApiSettings:
        """API instance settings"""
        return cast(
            ApiSettings, self.query_to_class(ApiSettings, _SETTINGS, path="settings")
        )

    def viewer(self) -> User:
        """Current logged in user"""
        return cast(User, self.query_to_class(User, _VIEWER, path="viewer"))

    @overload
    def project(self, id: str) -> Project:  # type: ignore
        """Retrieve a project by ID"""
        pass

    @overload
    def project(self, login: str, slug: str) -> Project:  # type: ignore
        """Retrieve a project by login and slug"""
        pass

    # def project(self, loginOrId: str, slug: str = None) -> Project:
    #     if slug:
    #         params = {"login": loginOrId, "slug": slug}
    #         query = _PROJECT_BY_NAME
    #     else:
    #         params = {"id": loginOrId}
    #         query = _PROJECT_BY_ID

    #     return cast(
    #         Project, self.query_to_class(Project, query, path="project", params=params)
    #     )

    def project(self, idOrSlug: str) -> Project:
        if idOrSlug.__contains__("/"):
            tokens = idOrSlug.split("/")
            params = {"login": tokens[0], "slug": tokens[1]}
            query = _PROJECT_BY_NAME

        if not idOrSlug.__contains__("/"):
            params = {"id": idOrSlug}
            query = _PROJECT_BY_ID

        return cast(
            Project, self.query_to_class(Project, query, path="project", params=params)
        )

    def file(self, id: str) -> File:
        return cast(
            File, self.query_to_class(File, _FILE, path="file", params={"fileId": id})
        )

    def upload_to_default_filesource(
        self,
        project: Project,
        file: IO,
        storageFolderName=None,
        dataset: Dataset = None,
        **kwargs,
    ):
        """Takes in a project, file, and optional dataset, and uploads the file to DataTorch Storage"""
        storageId = project.storage_link_default().id
        storageFolderName = "" if storageFolderName is None else storageFolderName
        datasetId = "" if dataset is None else dataset.id
        importFiles = "false" if dataset is None else "true"
        endpoint = f"{self.api_url}/file/v1/upload/{storageId}?path={storageFolderName}&import={importFiles}&datasetId={datasetId}"

        if magic:
            # save the current position
            tell = file.tell()
            # read 1024 bytes and get the mimetype
            mimetype = magic.from_buffer(file.read(1024), mime=True)
            # go back to the saved position
            file.seek(tell)
        else:
            mimetype = mimetypes.guess_type(file.name)[0]

        r = requests.post(
            endpoint,
            files={"file": (os.path.basename(file.name), file, mimetype)},
            headers={self.token_header: self._api_token},
            stream=True,
        )
        print(r.text + " " + endpoint)

    def glob_upload_folder(
        self,
        project: Project,
        uploadingFromGlob: str,
        storageFolderName: str,
        folderSplit=1000,
        dataset: Dataset = None,
        recursive=False,
        **kwargs,
    ):
        """Uploads a folder of files to DataTorch Storage, creating a new folder in storage for every 1000 files"""
        folderIndex = 0
        useFolderIndexes = False
        file_list = glob.glob(uploadingFromGlob, recursive=recursive)
        if file_list.__len__() > 1000:
            useFolderIndexes = True

        uploadFolderName = (
            storageFolderName
            if not useFolderIndexes
            else storageFolderName + "_" + str(folderIndex)
        )
        uploadCount = 0

        for file in file_list:
            if uploadCount != 0 and uploadCount % folderSplit == 0:
                folderIndex += 1
                uploadFolderName = storageFolderName + "_" + str(folderIndex)
            file = open(file, "rb")
            self.upload_to_default_filesource(
                project=project,
                file=file,
                storageFolderName=uploadFolderName,
                dataset=dataset,
            )
            uploadCount += 1

        print(
            str(uploadCount)
            + " files uploaded, into "
            + str(folderIndex + 1)
            + " created folders"
        )

    # def files(self, where: Where = None, limit: int = 400) -> List[File]:
    #     return []

    def validate_endpoint(self) -> bool:
        """Returns true if provided endpoint is correct."""
        try:
            version = self.settings().api_version
            logger.info("Endpoint API version: {}".format(version))
            return True
        except ConnectionRefusedError:
            return False
