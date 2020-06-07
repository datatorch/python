from logging import Logger, LoggerAdapter


class PrefixLogger(LoggerAdapter):
    """ A logger adapter that adds a prefix to every message """

    def __init__(self, logger: Logger, prefix: str):
        super(LoggerAdapter, self).__init__()
        self.logger = logger
        self.prefix = prefix

    def process(self, msg: str, kwargs: dict) -> (str, dict):
        return (f"[{self.prefix}] " + msg, kwargs)
