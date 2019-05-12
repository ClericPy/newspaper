import json
import logging
import os


def init_logger(logger_name=None):
    formatter_str = (
        "%(asctime)s %(levelname)-5s %(filename)s(%(lineno)s): %(message)s")
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(formatter_str, datefmt=datefmt)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    hl = logging.StreamHandler()
    hl.setFormatter(formatter)
    hl.setLevel(logging.INFO)
    logger.addHandler(hl)
    return logger


logger = init_logger()

global_configs = os.getenv('newspaper_config')
if global_configs:
    global_configs = json.loads(global_configs)
else:
    newspaper_config_template = '{"anti_gfw": {"url": "xxx"}, "mysql_config": {"mysql_host": "xxx", "mysql_port": 0, "mysql_user": "xxx", "mysql_password": "xxx", "mysql_db": "xxx"}}'
    logger.error(
        f'environment variable `newspaper_config` not found, it should be set as json like: {newspaper_config_template}'
    )
    raise RuntimeError('environment variable `newspaper_config` not found')

from .models import MySQLStorage
db = MySQLStorage(global_configs['mysql_config'])
