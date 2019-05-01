import asyncio

import aiomysql

from ..config import global_configs, get_logger
from ..storage import MySQLStorage
from .spiders import online_spiders, outlands_request


def get_url_key(url: str) -> str:
    """通过 url 来计算 key, 一方面计算 md5, 另一方面净化无用参数."""
    return url


async def workflow():
    logger = get_logger('crawler')
    coros = [func() for func in online_spiders]
    done, fail = await asyncio.wait(coros, timeout=120)
    if fail:
        logger.warn(f'failing spiders: {len(fail)}')
    for task in done:
        items = task.result()
        print(items)
    # db = MySQLStorage(global_configs['mysql_config'])
    # result = await db.execute('desc articles')
