import logging


class LogUploader(object):
    def log(self, record):
        pass

    def process_log(self):
        pass

    def upload(self):
        pass


class LogUploaderHandler(logging.Handler):
    def __init__(self, uploader: LogUploader):
        logging.Handler.__init__(self)
        self.log_uploader = uploader

    def emit(self, record: logging.LogRecord):
        self.log_uploader.log(record)


class MetricsLogger(LogUploader):
    pass


class StepLogger(LogUploader):
    pass


class AgentLogger(LogUploader):
    pass
