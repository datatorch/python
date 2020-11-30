from uuid import UUID
from typing import TYPE_CHECKING

from datatorch.utils.thread_pool import ThreadJob, ThreadPool


if TYPE_CHECKING:
    from ..commit import Commit


class _DownloadCommitFile(ThreadJob):
    def __init__(self, commit_id: UUID, file_hash: str, file_name: str):
        super().__init__()
        self.commit_id = commit_id
        self.file_hash = file_hash
        self.file_name = file_name

    def run(self):
        print(f"downloading {self.file_name}")


def download_commit(commit: "Commit", wait: bool = True):
    download_pool = ThreadPool()
    for file_name, meta in commit.files():
        job = _DownloadCommitFile(commit.id, meta.get("hash").hex(), file_name)
        download_pool.enqueue(job)

    if wait:
        download_pool.shutdown()

    return download_pool
