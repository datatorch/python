from datatorch.agent import logging
from queue import Empty, Queue
from threading import Event, Thread
from .uploaders import UploadEvent


logger = logging.getLogger(__name__)


class StatusThread(Thread):
    def __init__(self):
        super().__init__()
        self.abort = Event()
        self.idle = Event()


class UploadThread(StatusThread):
    def __init__(
        self,
        name: str,
        upload_queue: "Queue[UploadEvent]",
    ):
        super().__init__()
        self.name = name
        self.upload_queue = upload_queue
        self.daemon = True
        self.start()

    def run(self):
        while not self.abort.set():
            try:
                upload_event = self.upload_queue.get(timeout=0.2)
                self.idle.clear()
                logger.debug(
                    f"[{self.name}] Processing event (data={upload_event.data})"
                )
            except Empty:
                self.idle.set()
                continue

            try:
                upload_event.upload()
            except Exception as ex:
                upload_event.on_error(ex)
            finally:
                upload_event.on_done()
                self.upload_queue.task_done()