from typing import Set, TYPE_CHECKING
from datatorch.agent import logging
from datatorch.utils.thread_pool import ThreadPool

if TYPE_CHECKING:
    from datatorch.artifacts.commit.commit import Commit


logger = logging.getLogger(__name__)


class UploadThreadPool(ThreadPool):
    def __init__(self) -> None:
        super().__init__()
        self.processed_commit: Set[Commit] = set([])

    def join(self):
        """ Wait for completion of all tasks in queue. """
        return self.queue.join()

    def shutdown(self):
        from .stats import get_upload_stats

        if not self.alive():
            return

        logger.debug("shuting down upload thread pool.")

        get_upload_stats().show_progress()
        get_upload_stats()._reset_bytes()

        self._mark_commits_as_committed()

        return super(UploadThreadPool, self).shutdown()

    def _mark_commits_as_committed(self):
        for commit in self.processed_commit:
            commit._mark_committed()


_upload_pool = UploadThreadPool()
_upload_pool.abort()


def get_upload_pool():
    global _upload_pool
    _upload_pool.run()
    return _upload_pool
