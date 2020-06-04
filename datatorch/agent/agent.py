import time


class Agent(object):
    def __init__(self, id: str, host: str = BASE_URL):
        self.id = id
        self.host = host
        self.api_url = f'{host}/api'

        while True:
            time.sleep(10)
