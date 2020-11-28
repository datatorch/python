from os import cpu_count
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
from typing import Callable, List, Union
import time

from requests.sessions import Session

from .upload import FileUpload
from .thread import StatusThread, UploadThread


class UploadThreadPool:
    def __init__(self, thread_count: int = None) -> None:
        self._session = Session()
        self._thread_count = thread_count or cpu_count() or 8
        self._queue: "Queue[FileUpload]" = Queue()
        self._threads: List[StatusThread] = []

    def run(self):
        if self.alive():
            return False
        self._threads = [
            UploadThread(str(i), self._queue) for i in range(self._thread_count)
        ]
        return True

    def join(self):
        """ Wait for completion of all tasks in queue. """
        return self._queue.join()

    def enqueue(self, file: FileUpload, block: bool = False, timeout: float = None):
        file.
        self._queue.put(file, block=block, timeout=timeout)

    def alive(self):
        return True in [t.is_alive() for t in self._threads]

    def idle(self):
        return False not in [i.idle.is_set() for i in self._threads]

    def done(self):
        return self._queue.empty()

    def abort(self, block: bool = False):
        for a in self._threads:
            a.abort.set()

        while block and self.alive():
            return self._sleep()

    def _sleep(self):
        time.sleep(0.5)