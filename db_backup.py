#! pipenv run python
"""
从线上拉数据到本地备份 sqlite
"""
import re

from torequests import tPool
from torequests.utils import ttime, time

from newspaper.models import Sqlite3Storage, logger
from newspaper.config import ONLINE_HOST


def fetch_artcles(ts_start):
    req = tPool()
    api = f'https://{ONLINE_HOST}/newspaper/articles.query.json'
    next_url = ''
    start_params = {
        'query': '',
        'start_time': ts_start,
        'end_time': '',
        'source': '',
        'lang': 'ANY',
        'order_by': 'ts_update',
        'sorting': 'asc',
        'limit': '100',
        'offset': '0',
    }

    while 1:
        params = {} if next_url else start_params
        # 没有 next_url 的时候访问第一页, 有的时候访问 next_url
        url = next_url or api
        r = req.get(url, params=params, retry=2, timeout=10)
        if not r.x:
            logger.error(f'req init failed: {r.x}, {r.text}')
            raise IOError
        rj = r.json()
        articles = rj.get('articles', [])
        if articles:
            yield articles
        next_url = rj.get('next_url', '')
        if not (articles and next_url):
            # 没有文章, 并没有下一页
            logger.info(f'fetch_artcles finished, last url: {url}')
            return
        next_url = re.sub('^/', f'https://{ONLINE_HOST}/', next_url)


def get_ts_latest(cursor):
    cursor.execute('select max(ts_update) from articles')
    result = cursor.fetchone()[0]
    if result:
        return result
    else:
        return ttime(0)


def main():
    db = Sqlite3Storage(file_path='backup.sqlite')
    db._ensure_article_table_exists()
    ts_latest = get_ts_latest(db.cursor)
    logger.info(f'sync articles from online api: ts_latest={ts_latest}')
    article_cnt = 0
    for articles in fetch_artcles(ts_latest):
        db.add_articles(articles)
        article_cnt += len(articles)
        logger.info(f'+ {len(articles)} articles => {article_cnt}')
    logger.info(f'+ {article_cnt} new articles.')


if __name__ == "__main__":
    main()
    time.sleep(3)
