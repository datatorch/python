import logging

from datatorch.core import BASE_URL


logger = logging.getLogger(__name__)


class Agent(object):
    def __init__(self, id: str, host: str = BASE_URL):
        self.id = id
        self.host = host
        self.api_url = f'{host}/api'
        self.logger = logger

        self.logger.debug(f'Initializing agent with ID {id}')
        self.connect()

    def connect(self):
        self.logger.debug(f'Attempting connection to {self.api_url}')
