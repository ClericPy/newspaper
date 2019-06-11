import asyncio

from torequests.dummy import Requests

from ..config import db, spider_logger
from .spiders import history_spiders, online_spiders


async def test_spider_workflow():
    from .spiders import test_spiders
    from pprint import pprint

    for func in test_spiders:
        print('test start:', func.__doc__)
        articles = await func()
        # check schema
        for item in articles:
            assert (not item.get('desc')) or isinstance(item['desc'], str)
            assert (not item.get('ts_publish')) or isinstance(
                item['ts_publish'], str)
            assert (not item.get('cover')) or isinstance(item['cover'], str)
            assert isinstance(item.get('level'), int)
            assert isinstance(item.get('source'), str)
            assert isinstance(item.get('title'), str)
            assert isinstance(item.get('url'), str)
            if item.get('desc'):
                item['desc'] = item['desc'][:100]
        pprint(articles)


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
    # 生成一个 function name → source name 的映射
    function_sources = {func.__name__: func.__doc__ for func in online_spiders}
    coros = [func() for func in online_spiders]
    done, fail = await asyncio.wait(coros, timeout=120)
    spider_logger.info(f'{"=" * 30}')
    if fail:
        spider_logger.warn(f'failing spiders: {len(fail)}')
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            for task in done:
                articles = task.result()
                func_name = task._coro.__name__
                source_name = function_sources.get(func_name, func_name)
                if articles:
                    insert_result = await db.add_articles(articles,
                                                          cursor=cursor)
                else:
                    insert_result = 0
                spider_logger.info(
                    f'+ {insert_result} / {len(articles)} articles.\t[{source_name}]{"" if articles else " ?????????"}'
                )
    await clear_cache()


async def history_workflow():
    if not history_spiders:
        spider_logger.info('ignore for no history_spiders online.')
        return
    # 确认 articles 表存在, 否则建表
    await db._ensure_article_table_exists()
    # 生成一个 function name → source name 的映射
    function_sources = {func.__name__: func.__doc__ for func in history_spiders}
    coros = [func() for func in history_spiders]
    done, fail = await asyncio.wait(coros, timeout=9999)
    spider_logger.info(f'{"=" * 30}')
    if fail:
        spider_logger.warn(f'failing spiders: {len(fail)}')
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            for task in done:
                articles = task.result()
                func_name = task._coro.__name__
                source_name = function_sources.get(func_name, func_name)
                if articles:
                    insert_result = await db.add_articles(articles,
                                                          cursor=cursor)
                else:
                    insert_result = 0
                spider_logger.info(
                    f'+ {insert_result} / {len(articles)} articles.\t[{source_name}]{"" if articles else " ?????????"}'
                )
    await clear_cache()
