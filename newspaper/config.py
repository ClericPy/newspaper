import json
import logging
import os


def init_logger(api):
    formatter_str = (
        "%(asctime)s %(levelname)-5s %(filename)s(%(lineno)s): %(message)s")
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(formatter_str, datefmt=datefmt)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    hl = logging.StreamHandler()
    hl.setFormatter(formatter)
    hl.setLevel(logging.INFO)
    logger.addHandler(hl)
    api.logger = logger
    return api


global_configs = os.getenv('newspaper_config')
if global_configs:
    global_configs = json.loads(global_configs)
else:
    raise RuntimeError('environment variable `newspaper_config` not found')

# db_instance = 'sqlite'
# db_instance = 'mongodb'
db_instance = 'mysql'
