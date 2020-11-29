from datatorch.agent import logging
from os import cpu_count
from queue import Queue
from typing import List, TYPE_CHECKING
import time

from datatorch.utils import exithook

from .thread import StatusThread, UploadThread

if TYPE_CHECKING:
    from .events import UploadEvent


logger = logging.getLogger(__name__)


class UploadThreadPool:
    def __init__(self, thread_count: int = None, sample_time: float = 0.5) -> None:
        self._sample_time = sample_time
        self._thread_count = thread_count or cpu_count() or 16
        self.queue: "Queue[UploadEvent]" = Queue()
        self._threads: List[StatusThread] = []

    def run(self):
        if self.alive():
            return False

        logger.debug(f"creating {self._thread_count} upload threads")
        self._threads = [
            UploadThread(str(i), self.queue) for i in range(self._thread_count)
        ]
        exithook.register(self.shutdown)
        return True

    def join(self):
        """ Wait for completion of all tasks in queue. """
        return self.queue.join()

    def enqueue(self, file: "UploadEvent", block: bool = False, timeout: float = None):
        self.queue.put(file, block=block, timeout=timeout)

    def alive(self):
        return True in [t.is_alive() for t in self._threads]

    def idle(self):
        return False not in [i.idle.is_set() for i in self._threads]

    def done(self):
        return self.queue.qsize() == 0 and self.idle()

    def abort(self, block: bool = False):
        for a in self._threads:
            a.abort.set()

        while block and self.alive():
            return self._sleep()

    def _sleep(self):
        time.sleep(self._sample_time)

    def shutdown(self):
        from .stats import get_upload_stats

        if not self.alive():
            return

        logger.debug("shuting down upload thread pool.")

        get_upload_stats().show_progress()
        get_upload_stats()._reset_bytes()
        self.abort()
        self.join()
        logger.debug("done.")


upload_pool = UploadThreadPool()
upload_pool.abort()


def get_upload_pool():
    global upload_pool
    upload_pool.run()
    return upload_pool
