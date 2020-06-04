import threading
import time


class SystemStats(object):

    samples: int = 0

    def __init__(self, sample_rate: float = 0.2):
        self._thread = threading.Thread(target=self._monitor)
        self.sample_rate = sample_rate

    def start(self):
        self._thread.start()

    def _monitor(self):
        while True:
            self.samples += 1
            time.sleep(self.sample_rate)

    def stats(self):
        return {}
