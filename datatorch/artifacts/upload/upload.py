from requests.sessions import Session
from datatorch.artifacts.filesync import FileUpload
from typing import Callable


FileUploadProgressCallable = Callable[[int]]
FileUploadCallable = Callable[[FileUpload, FileUploadProgressCallable]]

import requests
from pathlib import Path
from typing import Callable


def azure_upload():
    pass


def gcp_upload():
    pass


def aws_upload():
    pass


class FileUpload:
    def __init__(
        self, job: str, path: Path, url: str, on_success: Callable, on_error: Callable
    ):
        self.job = job
        self.path = path
        self.url = url
        self.on_success = on_success
        self.on_error = on_error
        self.session = Session()

    def upload(self):
        try:
            upload = self.get_upload_func()
            upload(self)
            self.on_success()
        except:
            self.on_error()

    def get_upload_func(self) -> "Callable[[FileUpload, Callable]]":
        def upload_func():
            return self

        return upload_func
