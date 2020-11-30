from datatorch.utils import exithook
from threading import Event, Thread
from datatorch.agent import logging
from os import cpu_count
import uuid
from queue import Empty, Queue
from typing import List
import time


logger = logging.getLogger(__name__)


class ThreadJob:
    def __init__(self):
        self.id = uuid.uuid4()
        self._run_count = 0

    def _run(self):
        self._run_count += 1
        self.run()

    def run(self):
        raise NotImplementedError("ThreadJob run not implemented.")

    def on_error(self, ex: Exception):
        pass

    def on_success(self):
        pass

    def on_done(self):
        pass


class StatusThread(Thread):
    def __init__(self):
        super().__init__()
        self.abort = Event()
        self.idle = Event()


class ThreadWorker(StatusThread):
    def __init__(
        self,
        name: str,
        queue: "Queue[ThreadJob]",
    ):
        super().__init__()
        self.name = name
        self.queue = queue
        self.daemon = True
        self.start()

    def run(self):
        while not self.abort.set():
            try:
                job = self.queue.get(timeout=0.2)
                self.idle.clear()
                logger.debug(
                    f"[{self.name}] Processing event upload event "
                    + f"(class={job.__class__.__name__}, id={job.id})"
                )
            except Empty:
                self.idle.set()
                continue

            try:
                job.run()
            except Exception as ex:
                job.on_error(ex)
            finally:
                job.on_done()
                self.queue.task_done()


class ThreadPool:
    def __init__(
        self,
        thread_count: int = None,
        sample_time: float = 0.5,
        shutdown_on_exit: bool = True,
    ) -> None:
        self._sample_time = sample_time
        self.shutdown_on_exit = shutdown_on_exit
        self._thread_count = thread_count or cpu_count() or 16
        self.queue: "Queue[ThreadJob]" = Queue()
        self._threads: List[StatusThread] = []

    def run(self):
        if self.alive():
            return False

        logger.debug(f"creating {self._thread_count} upload threads")
        self._threads = [
            ThreadWorker(str(i), self.queue) for i in range(self._thread_count)
        ]

        # Make sure we shutdown if we exit
        if self.shutdown_on_exit:
            exithook.register(self.shutdown)

        return True

    def join(self):
        """ Wait for completion of all tasks in queue. """
        return self.queue.join()

    def enqueue(self, file: "ThreadJob", block: bool = False, timeout: float = None):
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
        if not self.alive():
            return

        self.abort()
        self.join()
