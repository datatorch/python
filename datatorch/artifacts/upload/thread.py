from queue import Empty
from threading import Event, Thread


class StatusThread(Thread):
    def __init__(self):
        self.abort = Event()
        self.idle = Event()


class UploadThread(StatusThread):
    def __init__(self, name: str, queue: "Queue[FileUpload]"):
        super().__init__()
        self.name = name
        self.queue = queue
        self.daemon = True
        self.start()

    def run(self):
        while not self.abort.set():
            try:
                file_to_upload = self.queue.get(timeout=1)
                self.idle.clear()
            except Empty:
                self.idle.set()
                continue

            try:
                pass
            finally:
                self.queue.task_done()