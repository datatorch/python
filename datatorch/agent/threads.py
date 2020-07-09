import time
import json
import psutil
import logging
import platform
import threading
import asyncio

from datetime import datetime, timezone
from .loop import Loop

logger = logging.getLogger(__name__)


class AgentSystemStats(object):
    @staticmethod
    def initial_stats():
        """ Returns stats that do not change over time. """
        # initialize averaging
        psutil.cpu_percent()
        cpu_freq = psutil.cpu_freq()
        mem = psutil.virtual_memory()

        return {
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
        la_1, la_5, la_15 = [(x / psutil.cpu_count()) for x in psutil.getloadavg()]
        return {
            "sampledAt": datetime.now(timezone.utc).isoformat()[:-9] + "Z",
            "cpuUsage": psutil.cpu_percent(),
            "avgLoad1": la_1,
            "avgLoad5": la_5,
            "avgLoad15": la_15,
            "memoryUsage": mem.percent,
            "diskUsage": psutil.disk_usage("/").percent,
        }

    def __init__(self, agent, sample_rate=60):
        self.agent = agent
        self.sample_rate = sample_rate

    async def start(self):
        logger.info("Sending initial metrics")
        await self.agent.api.initial_metrics(self.initial_stats())

        logger.info("Starting system monitoring thread.")
        await self._task_monitoring()

    async def _task_monitoring(self):
        logger.debug(f"Sampling system stats every {self.sample_rate} seconds.")
        psutil.cpu_percent()

        while True:
            stats = self.stats()
            loop = asyncio.get_event_loop()
            loop.create_task(self.agent.api.metrics(stats))
            await asyncio.sleep(self.sample_rate)
