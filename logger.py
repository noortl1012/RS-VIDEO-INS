import logging

class ColoredLogger:
    COLORS = {
        'DEBUG': '\033[92m',    # Green
        'INFO': '\033[94m',     # Blue
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',    # Red
        'RESET': '\033[0m'      # Reset to default
    }

    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)  # Set log level as needed

    def colored_log(self, level, message):
        color = self.COLORS.get(level, self.COLORS['RESET'])
        self.logger.log(level, f"{color}{message}{self.COLORS['RESET']}")

    def debug(self, message):
        self.colored_log(logging.DEBUG, message)

    def info(self, message):
        self.colored_log(logging.INFO, message)

    def warning(self, message):
        self.colored_log(logging.WARNING, message)

    def error(self, message):
        self.colored_log(logging.ERROR, message)
