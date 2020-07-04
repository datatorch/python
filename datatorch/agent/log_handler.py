import logging
from datatorch.api import ApiClient


class AgentAPIHandler(logging.Handler):
    def __init__(self, api: ApiClient, size: int = 2):
        logging.Handler.__init__(self)
        self.api = api
        self.records = []
        self.size = size

    def emit(self, record: logging.LogRecord):

        self.records.append(record)

        if len(self.records) >= self.size:
            self.upload()

    def upload(self):
        self.records = []
