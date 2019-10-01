import logging
import pathlib
from logging.handlers import RotatingFileHandler

log_dir = pathlib.Path(__file__).absolute().parent.parent / 'logs'


def init_logger(logger_name=None, file_name='server.log', max_mb=100):
    if not log_dir.is_dir():
        log_dir.mkdir()
    formatter_str = (
        "%(asctime)s %(levelname)-5s [%(name)s] %(filename)s(%(lineno)s): %(message)s"
    )
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(formatter_str, datefmt=datefmt)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    stream_hl = logging.StreamHandler()
    stream_hl.setFormatter(formatter)
    stream_hl.setLevel(logging.INFO)
    logger.addHandler(stream_hl)

    file_hl = RotatingFileHandler(filename=log_dir / file_name,
                                  maxBytes=1024 * 1024 * max_mb,
                                  encoding='utf-8')
    file_hl.setFormatter(formatter)
    file_hl.setLevel(logging.INFO)
    logger.addHandler(file_hl)
    return logger


logger = init_logger('server', 'server.log')
spider_logger = init_logger('spider_logger', 'spider.log', max_mb=10)
