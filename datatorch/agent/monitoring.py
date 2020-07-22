import psutil
import logging
import platform
import asyncio

from datetime import datetime, timezone
from datatorch.utils.package import get_version

logger = logging.getLogger(__name__)


def print_stats(metrics):
    cpuUsage = metrics.get("cpuUsage")
    memUsage = metrics.get("memoryUsage")
    diskUsage = metrics.get("diskUsage")
    logger.debug(
        f"System stats: CPU: {cpuUsage}, Memory: {memUsage}, Disk: {diskUsage}"
    )


class AgentSystemStats(object):
    @staticmethod
    def initial_stats():
        """ Returns stats that do not change over time. """
        # initialize averaging
        psutil.cpu_percent()
        cpu_freq = psutil.cpu_freq()
        mem = psutil.virtual_memory()

        return {
            "version": get_version(),
            "os": platform.system(),
            "osRelease": platform.release(),
            "osVersion": platform.version(),
            "pythonVersion": platform.python_version(),
            "totalMemory": round(mem.total / 1024),
            "cpuName": platform.processor(),
            "cpuFreqMin": cpu_freq.min,
            "cpuFreqMax": cpu_freq.max,
            "cpuCoresPhysical": psutil.cpu_count(logical=False),
            "cpuCoresLogical": psutil.cpu_count(logical=True),
        }

    @staticmethod
    def stats():
        mem = psutil.virtual_memory()
        la_1, la_5, la_15 = psutil.getloadavg()
        stats = {
            "sampledAt": datetime.now(timezone.utc).isoformat()[:-9] + "Z",
            "avgLoad1": la_1,
            "avgLoad5": la_5,
            "avgLoad15": la_15,
            "cpuUsage": psutil.cpu_percent(),
            "memoryUsage": mem.percent,
            "diskUsage": psutil.disk_usage("/").percent,
        }
        print_stats(stats)
        return stats

    def __init__(self, agent, sample_rate=60):
        self.agent = agent
        self.sample_rate = sample_rate
        self.sample = 0

    async def start(self):
        try:
            logger.info("Sending initial system metrics.")
            await self.agent.api.initial_metrics(self.initial_stats())

            logger.info("Starting system monitoring task.")
            await self._task_monitoring()
        except asyncio.CancelledError:
            logger.info("Exiting system monitoring task.")

    async def _task_monitoring(self):
        logger.debug(f"Sampling system stats every {self.sample_rate} seconds.")
        psutil.cpu_percent()

        while True:
            self.sample += 1
            stats = self.stats()
            loop = asyncio.get_event_loop()
            if self.sample != 1:
                loop.create_task(self.agent.api.metrics(stats))
            await asyncio.sleep(self.sample_rate)
