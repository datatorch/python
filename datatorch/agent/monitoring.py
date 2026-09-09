import psutil
import logging
import platform
import asyncio

from psutil._common import scpufreq
from datetime import datetime, timezone
from datatorch.utils.package import get_version
from collections import namedtuple

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
        """Returns stats that do not change over time."""
        # initialize averaging
        psutil.cpu_percent()

        # For M1 macs psutil doesnt work to get freq
        try:
            cpu_freq: scpufreq = psutil.cpu_freq()
        except:
            logger.info("CPU Freq could not be obtained and will be logged as 0.")
            cpu_freq = scpufreq(0, 0, 0)

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

    # Consecutive failed reports before the connection is considered dead.
    # The steps subscription can sit silently on a half-open socket (e.g.
    # after sleep); the report failing is the signal that reaches us.
    MAX_REPORT_FAILURES = 3
    REPORT_TIMEOUT = 30

    def __init__(self, agent, sample_rate=60):
        self.agent = agent
        self.sample_rate = sample_rate
        self.sample = 0
        self.report_failures = 0

    async def start(self):
        try:
            logger.info("Sending initial system metrics.")
            logger.info(self.initial_stats())
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
            if self.sample != 1:
                await self._report(stats)
            await asyncio.sleep(self.sample_rate)

    async def _report(self, stats):
        """Sends one metric report; repeated failures force a reconnect."""
        try:
            await asyncio.wait_for(
                self.agent.api.metrics(stats), timeout=self.REPORT_TIMEOUT
            )
            self.report_failures = 0
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.report_failures += 1
            logger.warning(
                f"Metric report failed ({self.report_failures}/{self.MAX_REPORT_FAILURES}): {e}"
            )
            if self.report_failures >= self.MAX_REPORT_FAILURES:
                logger.error("Connection looks dead; forcing a reconnect.")
                self.report_failures = 0
                await self.agent.api.force_reconnect()
