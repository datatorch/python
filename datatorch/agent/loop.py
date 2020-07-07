from typing import List
from asyncio import get_event_loop, Task, all_tasks


class Loop(object):
    @staticmethod
    def stop():
        get_event_loop().stop()

    @staticmethod
    def add_task(func) -> Task:
        return get_event_loop().create_task(func)

    @staticmethod
    def active_tasks() -> List[Task]:
        return [task for task in all_tasks() if not task.done()]

    @staticmethod
    def run_forever():
        get_event_loop().run_forever()
