import logging
from datatorch.core.upload.stats import get_upload_stats
import requests
from uuid import uuid4
from pathlib import Path
from typing import Generic, TypeVar


logger = logging.getLogger(__name__)
_session = requests.Session()


D = TypeVar("D")


class UploadEvent(Generic[D]):
    @staticmethod
    def session():
        return _session

    def __init__(self, data: D, url: str):
        if isinstance(data, Path) and not data.is_file():
            raise FileNotFoundError("Only files can be uploaded.")

        self.id = uuid4()
        self.data: D = data
        self.url = url

        # Number for how many times it has ran the upload command in an UploadThread.
        self.upload_count = 0

    def on_success(self):
        pass

    def on_error(self, ex: Exception):
        logger.error(ex)

    def on_done(self):
        pass

    def inc_upload_count(self):
        self.upload_count += 1

    def upload(self):
        raise NotImplementedError("Upload event not implemented.")


class PutUploadEvent(UploadEvent[Path]):
    def __init__(
        self,
        data: Path,
        url: str,
        extra_headers: dict = {},
        category: str = "put",
    ):
        super().__init__(data, url)
        self.category = category
        self.extra_headers = extra_headers

    def upload(self):
        with open(self.data, "rb") as buff:
            pbuff = get_upload_stats().add(self.category, buff)
            self.session().put(self.url, data=pbuff, headers=self.headers())

    def headers(self):
        headers = {
            # Azure blob type header
            "x-ms-blob-type": "BlockBlob"
        }
        return {**headers, **self.extra_headers}


class TusUploadEvent(UploadEvent[Path]):
    pass