import json
import logging
import os


def get_logger(logger_name):
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


global_configs = os.getenv('newspaper_config')
if global_configs:
    global_configs = json.loads(global_configs)
else:
    raise RuntimeError('environment variable `newspaper_config` not found')
