#! pipenv run python
"""
同时执行线上先下数据库
"""
import asyncio
import traceback
import logging

from newspaper.config import init_db
from newspaper.models import Sqlite3Storage, logger


async def main():
    db = Sqlite3Storage(file_path='backup.sqlite')
    db._ensure_article_table_exists()
    mysql = init_db()
    logger.setLevel(logging.WARNING)
    while 1:
        # select count(*) from articles
        # select count(*) from articles where `desc` like '%本文分享 方巍%'
        sql = input('Input SQL:\n')
        if not sql:
            break
        try:
            print(sql)
            db.cursor.execute(sql)
            logger.warning(f'Sqlite3Storage: {db.cursor.fetchall()}')
            result = await mysql.execute(sql)
            logger.warning(f'MysqlStorage: {result}')
        except KeyboardInterrupt:
            break
        except Exception:
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
