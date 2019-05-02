import asyncio

import aiomysql

from ..config import global_configs, crawler_logger
from ..storage import MySQLStorage
from .spiders import online_spiders, history_spiders


async def online_workflow():
    logger = crawler_logger
    # 确认 articles 表存在, 否则建表
    db = MySQLStorage(global_configs['mysql_config'])
    await db._ensure_article_table_exists()
    coros = [func() for func in online_spiders]
    done, fail = await asyncio.wait(coros, timeout=120)
    if fail:
        logger.warn(f'failing spiders: {len(fail)}')
    # print(done)
    for task in done:
        result = task.result()
        # print(result)
        if result:
            source_name, articles = result['source_name'], result['articles']
            insert_result = await db.add_articles(articles)


async def history_workflow():
    logger = crawler_logger
    # 确认 articles 表存在, 否则建表
    db = MySQLStorage(global_configs['mysql_config'])
    await db._ensure_article_table_exists()
    coros = [func() for func in history_spiders]
    done, fail = await asyncio.wait(coros, timeout=120)
    if fail:
        logger.warn(f'failing spiders: {len(fail)}')
    # print(done)
    for task in done:
        result = task.result()
        # print(result)
        if result:
            source_name, articles = result['source_name'], result['articles']
            insert_result = await db.add_articles(articles)
