import asyncio

import aiomysql
from torequests.dummy import Requests

from ..config import db, global_configs, spider_logger
from .spiders import history_spiders, online_spiders


async def test_spider_workflow():
    from .spiders import python_weekly

    result = await python_weekly()
    print(result)


async def clear_cache():
    url = 'http://127.0.0.1:9001/newspaper/articles.cache.clear'
    req = Requests()
    r = await req.get(url, timeout=2)
    spider_logger.info(f'clear_cache {r.text}')


async def online_workflow():
    if not online_spiders:
        spider_logger.info('no online_spiders online.')
        return
    # 确认 articles 表存在, 否则建表
    await db._ensure_article_table_exists()
    coros = [func() for func in online_spiders]
    done, fail = await asyncio.wait(coros, timeout=120)
    if fail:
        spider_logger.warn(f'failing spiders: {len(fail)}')
    # print(done)
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            for task in done:
                articles = task.result()
                # print(result)
                if articles:
                    insert_result = await db.add_articles(articles,
                                                          cursor=cursor)
                    spider_logger.info(
                        f'[{articles[0].get("source")}]: inserted {insert_result} of {len(articles)} articles. {"+" * (len(articles)//10)}'
                    )
    await clear_cache()


async def history_workflow():
    if not history_spiders:
        spider_logger.info('ignore for no history_spiders online.')
        return
    # 确认 articles 表存在, 否则建表
    await db._ensure_article_table_exists()
    coros = [func() for func in history_spiders]
    done, fail = await asyncio.wait(coros, timeout=120)
    if fail:
        spider_logger.warn(f'failing spiders: {len(fail)}')
    # print(done)
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            for task in done:
                articles = task.result()
                # print(result)
                if articles:
                    insert_result = await db.add_articles(articles,
                                                          cursor=cursor)
                    spider_logger.info(
                        f'[{articles[0].get("source")}]: inserted {insert_result} of {len(articles)} articles. {"+" * (len(articles)//10)}'
                    )
    await clear_cache()
