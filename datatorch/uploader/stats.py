from datatorch.utils.format import std_out_err_redirect_tqdm
import logging
import traceback
from tqdm import tqdm

from typing import Callable, Dict
from datatorch.utils.wrapper import Wrapper
from io import BufferedReader
from threading import Lock
import sys
import os


logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], None]


class FileChangingError(Exception):
    pass


class ProgressBufferedReader(Wrapper):
    __wraps__ = BufferedReader

    def __init__(self, file: BufferedReader, callback: ProgressCallback = None):
        super().__init__(file)
        self._file = file

        def _callback(_: int, __: int):
            return

        self.callback = callback or _callback
        self.read_bytes = 0
        self.total_bytes = os.fstat(file.fileno()).st_size

    def read(self, size: int = -1):

        bites = self._file.read(size)
        bytes_read = len(bites)
        self.read_bytes += bytes_read

        is_shrinking = not bites and self.read_bytes < self.total_bytes
        # is_growing = self.read_bytes > self.total_bytes
        if is_shrinking:
            raise FileChangingError(
                f"File size is shrinking (read={self.read_bytes}, size={self.total_bytes})."
            )

        self.callback(bytes_read, self.read_bytes)
        return bites

    def reset(self):
        self.seek(0)
        self.callback(-self.read_bytes, 0)
        self.read_bytes = 0


class UploadStatsLock:
    def __init__(self):
        self.__total_lock = Lock()
        self.__total_bytes = 0

        self.__uploaded_lock = Lock()
        self.__uploaded_bytes = 0

    def _add_total_bytes(self, value: int):
        with self.__total_lock:
            self.__total_bytes += value

    def _add_uploaded_bytes(self, value: int):
        with self.__uploaded_lock:
            self.__uploaded_bytes += value

    def _reset_bytes(self):
        with self.__total_lock:
            self.__total_bytes = 0
        with self.__uploaded_lock:
            self.__uploaded_bytes = 0

    @property
    def total_bytes(self):
        return self.__total_bytes

    @property
    def uploaded_bytes(self):
        return self.__uploaded_bytes


class UploadStats(UploadStatsLock):
    def __init__(self, category: "CategoryUploadStats" = None):
        super().__init__()
        self.files: Dict[str, BufferedReader] = {}
        self.category = category

    def add(self, br: BufferedReader) -> BufferedReader:
        file_found = self.files.get(br.name)
        if file_found and not file_found.closed:
            raise ValueError(f"Buffer '{br.name}' is already being monitored.")

        pbr = ProgressBufferedReader(br, self.__update_stats)
        self._add_total_bytes(pbr.total_bytes)
        logger.info(f"monitoring buffer upload progress ({br.name})")
        self.files[br.name] = pbr  # type: ignore
        return pbr  # type: ignore

    def __update_stats(self, read_bytes, _):
        self._add_uploaded_bytes(read_bytes)

    def _add_total_bytes(self, value: int):
        super()._add_total_bytes(value)
        if self.category:
            self.category._add_total_bytes(value)

    def _add_uploaded_bytes(self, value: int):
        super()._add_uploaded_bytes(value)
        if self.category:
            self.category._add_uploaded_bytes(value)

    @property
    def total_bytes(self):
        return self.__total_bytes

    @property
    def uploaded_bytes(self):
        return self.__uploaded_bytes


class CategoryUploadStats(UploadStatsLock):
    def __init__(self):
        super().__init__()
        self._category_lock = Lock()
        self._categories: Dict[str, UploadStats] = {}

    def add(self, category: str, br: BufferedReader):
        with self._category_lock:
            if self._categories.get(category) is None:
                self._categories[category] = UploadStats(self)
            buff = self._categories[category].add(br)
            return buff

    def remove(self, category: str, br: BufferedReader):
        with self._category_lock:
            stats = self._categories.get(category)
            if not stats:
                return

            buff = stats.files.get(br.name)
            if buff:
                del stats.files[br.name]

    def show_progress(self):
        from .pool import get_upload_pool

        is_done = get_upload_pool().done()


        if is_done:
            return

        with tqdm(
            desc="Uploading files",
            total=self.total_bytes,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            dynamic_ncols=True,
            file=sys.stdout,
        ) as pbar:
            prev = 0
            while not get_upload_pool().done():
                delta = self.uploaded_bytes - prev
                prev = self.uploaded_bytes
                pbar.update(delta)
                if pbar.total != self.total_bytes:
                    pbar.total = self.total_bytes
                    pbar.refresh()
            pbar.update(pbar.total - pbar.last_print_n)


_upload_stats = CategoryUploadStats()


def get_upload_stats():
    global _upload_stats
    return _upload_stats
