import asyncio

import aiomysql

from ..config import global_configs, crawler_logger
from ..storage import MySQLStorage
from .spiders import online_spiders, history_spiders


async def online_workflow():
    logger = crawler_logger
    if not online_spiders:
        logger.info('no online_spiders online.')
        return
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
            logger.info(
                f'{source_name}: crawled {len(articles)} articles, inserted {insert_result}'
            )


async def history_workflow():
    logger = crawler_logger
    if not history_spiders:
        logger.info('ignore for no history_spiders online.')
        return
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
            logger.info(
                f'{source_name}: crawled {len(articles)} articles, inserted {insert_result}'
            )
