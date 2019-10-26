import json
import logging
import os
import pathlib


def init_config():
    global_configs = os.getenv(
        'newspaper_config',
        None) or pathlib.Path('/var/newspaper.conf').read_text()
    if global_configs:
        global_configs = json.loads(global_configs)
    else:
        newspaper_config_template = '{"anti_gfw": {"url": "xxx"}, "mysql_config": {"mysql_host": "xxx", "mysql_port": 0, "mysql_user": "xxx", "mysql_password": "xxx", "mysql_db": "xxx"}}'
        logging.error(
            f'environment variable `newspaper_config` not found, it should be set as json like: {newspaper_config_template}'
        )
        raise RuntimeError('environment variable `newspaper_config` not found')
    return global_configs


def init_db():
    from .models import MySQLStorage
    db = MySQLStorage(global_configs['mysql_config'])
    return db


global_configs = init_config()
ONLINE_HOST = 'www.clericpy.top'
GA_ID = 'UA-150991415-2'
