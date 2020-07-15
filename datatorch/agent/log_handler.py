from datatorch.agent.client import AgentApiClient
import logging


class AgentAPIHandler(logging.Handler):
    def __init__(self, api: AgentApiClient, size: int = 2):
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
