import logging

class Logger:
    logger = None

    def __init__(self, level="INFO", name=__name__):
        logging.basicConfig(level=level)
        Logger.logger = logging.getLogger(name)