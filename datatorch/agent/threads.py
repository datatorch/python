import time
import json
import psutil
import logging
import platform
import threading


logger = logging.getLogger(__name__)


class AgentSystemStats(object):
    @staticmethod
    def initial_stats():
        """ Returns stats that do not change over time. """
        # initialize averaging
        psutil.cpu_percent()
        return {
            "os": platform.platform(),
            "python": {"version": platform.python_version()},
            "cpu": {
                "name": platform.processor(),
                "cores": {
                    "physical": psutil.cpu_count(logical=False),
                    "logical": psutil.cpu_count(logical=False),
                },
            },
        }

    @staticmethod
    def stats():
        cpu_usage = [x / psutil.cpu_count() * 100 for x in psutil.getloadavg()]
        return {
            "cpu": {"usage": cpu_usage},
            "disk": {"usage": psutil.disk_usage("/")},
        }

    def __init__(self, agent, sample_rate=2, start_monitoring=False):
        self.agent = agent
        self.samples = 0
        self.sample_rate = sample_rate

        self._stop_monitoring = False
        self._thread = threading.Thread(target=self._thread_monitoring)

        if start_monitoring:
            self.start()

    def start(self):
        logger.debug("Starting system monitoring thread.")
        self._thread.start()

    def stop(self):
        self._stop_monitoring = True

    def join(self):
        try:
            self._thread.join()
        # Incase we never started the thread
        except RuntimeError:
            pass

    def shutdown(self):
        self.stop()
        self.join()

    def _thread_monitoring(self):
        logger.debug("Sampling system stats every {} seconds.".format(self.sample_rate))

        psutil.cpu_percent()

        while True:
            self.samples += 1

            stats = self.stats()
            stats_json = json.dumps(stats)

            time_count = 0
            while time_count < self.sample_rate:
                time_count += 0.1
                time.sleep(0.1)
                if self._stop_monitoring:
                    logger.debug("Exiting system stats monitoring thread.")
                    return
