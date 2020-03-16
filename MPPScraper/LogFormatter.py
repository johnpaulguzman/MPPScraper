from Config import Config

import logging


class LogFormatter:
    date_format = "%H:%M:%S"
    format_templ = "[%(asctime)s/%(levelname)s]-[%(processName)s/%(filename)s/L%(lineno)d]: %(message)s"

    @staticmethod
    def attach_to_logger(logger):
        log_color_formatter = LogColorFormatter()
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logger.level)
        stream_handler.setFormatter(log_color_formatter)
        logger.addHandler(stream_handler)

        log_formatter = logging.Formatter(LogFormatter.format_templ, LogFormatter.date_format)
        file_handler = logging.FileHandler(Config.log_path, 'w', encoding='utf-8')
        file_handler.setLevel(logger.level)
        file_handler.setFormatter(log_formatter)
        logger.addHandler(file_handler)

    @staticmethod
    def configure_root_logger(ignored_loggers=('urllib3', 'selenium')):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        LogFormatter.attach_to_logger(root_logger)
        for logger_name in ignored_loggers:
            ignored_logger = logging.getLogger(logger_name)
            ignored_logger.setLevel(logging.CRITICAL)
        return root_logger

class LogColorFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""
    reset = '\033[0m'
    blue = '\033[0;34m'
    green = '\033[0;32m'
    yellow = '\033[0;33m'
    red = '\033[0;31m'
    magenta = '\033[0;35m'
    cyan = '\033[0;36m'

    FORMATS = {
        logging.DEBUG: blue + LogFormatter.format_templ + reset,
        logging.INFO: green + LogFormatter.format_templ + reset,
        logging.WARNING: yellow + LogFormatter.format_templ + reset,
        logging.ERROR: red + LogFormatter.format_templ + reset,
        logging.CRITICAL: magenta + LogFormatter.format_templ + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, LogFormatter.date_format)
        return formatter.format(record)
