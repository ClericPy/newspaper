import json
import logging
import os
import pathlib
from logging.handlers import RotatingFileHandler


def init_logger(logger_name=None, file_name='server.log'):
    log_dir = pathlib.Path(__file__).parent / 'logs'
    if not log_dir.is_dir():
        log_dir.mkdir()
    formatter_str = (
        "%(asctime)s %(levelname)-5s %(filename)s(%(lineno)s): %(message)s")
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(formatter_str, datefmt=datefmt)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    stream_hl = logging.StreamHandler()
    stream_hl.setFormatter(formatter)
    stream_hl.setLevel(logging.INFO)
    logger.addHandler(stream_hl)

    file_hl = RotatingFileHandler(filename=log_dir / file_name,
                                  maxBytes=1024 * 1024 * 100,
                                  encoding='utf-8')
    file_hl.setFormatter(formatter)
    file_hl.setLevel(logging.INFO)
    logger.addHandler(file_hl)
    return logger


def init_config():
    global_configs = os.getenv('newspaper_config')
    if global_configs:
        global_configs = json.loads(global_configs)
    else:
        newspaper_config_template = '{"anti_gfw": {"url": "xxx"}, "mysql_config": {"mysql_host": "xxx", "mysql_port": 0, "mysql_user": "xxx", "mysql_password": "xxx", "mysql_db": "xxx"}}'
        logger.error(
            f'environment variable `newspaper_config` not found, it should be set as json like: {newspaper_config_template}'
        )
        raise RuntimeError('environment variable `newspaper_config` not found')
    return global_configs


def init_db():
    from .models import MySQLStorage
    db = MySQLStorage(global_configs['mysql_config'])
    return db


logger = init_logger()
access_logger = init_logger('access_logger', 'access.log')
spider_logger = init_logger('spider_logger', 'spider.log')
global_configs = init_config()
db = init_db()
