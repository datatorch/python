import functools
from datatorch.utils.files import mkdir_exists
from uuid import UUID
from typing import Optional, TYPE_CHECKING, Union, cast
from typing_extensions import TypedDict
from pathlib import Path

from requests import Session
from requests.adapters import Retry
from requests.sessions import HTTPAdapter

from datatorch.uploader import get_upload_stats
from datatorch.api.client import Client

from .directory import ArtifactDirectory

if TYPE_CHECKING:
    from .commit.commit import Commit, CommitStatus


class ArtifactExistsError(Exception):
    pass

class CommitExistsError(Exception):
    pass


class UploadSession(Session):
    def __init__(self):
        super().__init__()
        retries = Retry(
            total=10,
            backoff_factor=1,
            status_forcelist=(408, 409, 429, 500, 502, 503, 504),
            redirect=5,
        )
        adapter = HTTPAdapter(
            # Keeps retrying for ~20 mins
            max_retries=retries
        )
        self.mount("http://", adapter)
        self.mount("https://", adapter)


class CommitEntity(TypedDict):
    id: str
    message: str
    status: str
    artifactId: str
    parentId: str


class ArtifactEntity(TypedDict):
    id: str
    name: str
    latest: Optional[CommitEntity]


_api: "Optional[ArtifactsApi]" = None


class ArtifactsApi(Client):
    @classmethod
    def instance(cls):
        global _api
        if _api is None:
            _api = cls()
        return _api

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = UploadSession()
        self.artifact_dir = ArtifactDirectory()
        self.file_v2_url = f"{self.api_url}/file/v2"

    def _download_redirect(self, url: str, path: Path):
        url = f"{self.file_v2_url}/{url}"
        headers = {
            self.token_header: self._api_token,
            # Azure blob type header
            "x-ms-blob-type": "BlockBlob",
        }
        mkdir_exists(str(path.parent))
        with self._session.get(url, headers=headers, stream=True) as stream, open(
            path, "wb"
        ) as file:
            for chuck in stream.iter_content(chunk_size=8192):
                file.write(chuck)

    def _upload_redirect(self, url: str, path: Path, category: str = "file"):
        url = f"{self.file_v2_url}/{url}"
        res = self._session.put(url, allow_redirects=False)
        headers = {
            self.token_header: self._api_token,
            # Azure blob type header
            "x-ms-blob-type": "BlockBlob",
        }
        if res.status_code == 307 or res.status_code == 302:
            with open(path, "rb") as buff:
                new_url = res.headers["Location"]
                pbuff = get_upload_stats().add(category, buff)
                self._session.put(
                    new_url,
                    data=pbuff,
                    headers=headers,
                    allow_redirects=True,
                )

    def upload_artifact_file(
        self, artifact_id: Union[str, UUID], file_path: Path, file_hash: str
    ):
        url = f"artifact/{str(artifact_id)}/file/{file_hash}"
        self._upload_redirect(url, file_path, category="artifact")

    def upload_commit_manifest(self, commit_id: Union[str, UUID], manifest_path: Path):
        url = f"commit/{str(commit_id)}/manifest"
        self._upload_redirect(url, manifest_path, category="artifact")

    def upload_commit_migration(
        self, commit_id: Union[str, UUID], migration_path: Path
    ):
        url = f"commit/{str(commit_id)}/migration"
        self._upload_redirect(url, migration_path, category="artifact")

    def download_commit_manifest(self, commit_id: Union[str, UUID]):
        url = f"commit/{str(commit_id)}/manifest"
        path = Path(self.artifact_dir.commit_manifest(commit_id))
        if path.exists():
            return path

        self._download_redirect(url, path)
        return path

    # def create_artifact(self, login: str, project: str, name: str) -> ArtifactEntity:
    #     res = self.execute(
    #         """
    #         mutation CreateArtifact($login: String!, $project: String!, $name: String!) {
    #             artifact: createArtifact()
    #         }
    #         """
    #     )

    def artifact_by_name(self, login: str, project: str, name: str) -> ArtifactEntity:
        res = self.execute(
            """
            query GetArtifact($login: String!, $project: String!, $name: String!) {
                artifact: artifactByName(login: $login, project: $project, name: $name) {
                    id
                    name
                    latest {
                        id
                        status
                        message
                        artifactId
                        parentId
                    }
                }
            }
            """,
            params=dict(login=login, project=project, name=name),
        )
        artifact = res.get("artifact")
        if artifact is None:
            raise ArtifactExistsError(
                "Artifact does not exist. Use `Artifact.create(...)` to create a new artifact."
            )
        return cast(ArtifactEntity, artifact)

    def commit(self, id: UUID) -> CommitEntity:
        res = self.execute(
            """
            query GetCommit($id: ID!) {
                commit: commit(id: $id) {
                    id
                    message
                    # tags
                    status
                    parentId
                }
            }
            """,
            params=dict(id=str(id)),
        )
        commit = res.get("commit")
        if commit is None:
            raise CommitExistsError("Commit does not exist.")
        return cast(CommitEntity, commit)

    def create_commit(
        self,
        commit_id: str,
        artifact_id: str,
        parent_id: str = None,
        status: "CommitStatus" = None,
        message: str = None,
    ):
        res = self.execute(
            """
            mutation CreateArtifactCommit(
                $commitId: ID!
                $artifactId: ID!
                $status: ArtifactCommitStatus
                $message: String
                $parentId: ID
            ) {
                commit: createArtifactCommit(
                    input: {
                        id: $commitId
                        artifactId: $artifactId
                        status: $status
                        message: $message
                        parentId: $parentId
                    }
                ) {
                    id
                }
            }
            """,
            params=dict(
                commitId=commit_id,
                artifactId=artifact_id,
                status=str(status),
                message=message,
                parentId=parent_id,
            ),
        )
        return res.get("commit") is not None
