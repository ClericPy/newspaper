import abc
import asyncio
import datetime
import typing
import warnings

import aiomysql
from torequests.utils import json, ttime

from .config import global_configs, logger

# 用了 insert ignore 还总是 warning, 又不想 insert try, 只好全禁掉了...
# warnings.filterwarnings('ignore', category=aiomysql.Warning)


class Storage(object, metaclass=abc.ABCMeta):
    """存储器抽象. 统一参数对文章数据库进行增删改查."""
    max_limit = 100  # 避免 limit 设置的太大一次提取太多导致拥堵
    articles_table_columns = ('id', 'url_key', 'title', 'url', 'cover', 'desc',
                              'source', 'level', 'featured', 'ts_publish',
                              'ts_create', 'ts_update')

    def format_output_articles(self, articles: typing.Sequence[dict]):
        dt_type = datetime.datetime
        for article in articles:
            for key, value in article.items():
                if isinstance(value, dt_type):
                    article[key] = str(value)
        return articles

    def ensure_articles(self, articles: typing.Sequence[dict]) -> list:
        valid_articles = []
        # ensure_keys = ("url_key", "title", "cover", "desc", "source",
        #                "featured", "ts_publish")
        now = ttime()
        keys_set = None
        for article in articles:
            if not isinstance(article, dict):
                continue
            if not keys_set:
                keys_set = set(article.keys())
            else:
                # 如果 keys 和第一个不一样, 就没法使用 executemany, 所以跳过
                if set(article.keys()) != keys_set:
                    continue
            if not (article.get('url_key') and article.get('title') and
                    article.get('url')):
                continue
            article.setdefault('cover', '')
            article.setdefault('desc', '')
            article.setdefault('source', 'unknown')
            article.setdefault('featured', 0)
            article.setdefault('level', 3)
            article.setdefault('ts_publish', now)
            valid_articles.append(article)
        return valid_articles

    @abc.abstractmethod
    async def add_articles(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def del_articles(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def update_articles(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def query_articles(self, *args, **kwargs):
        raise NotImplementedError


class MySQLStorage(Storage):
    """连接 mysql 线上数据库, 目前不需要读写分离, 因为只初始化一次, 所以不需要单例."""

    def __init__(self, mysql_config):
        self.host = mysql_config['mysql_host']
        self.port = mysql_config['mysql_port']
        self.user = mysql_config['mysql_user']
        self.password = mysql_config['mysql_password']
        self.db = mysql_config['mysql_db']
        self.autocommit = True
        self.pool_recycle = 7 * 3600
        self.connect_args = dict(host=self.host,
                                 port=self.port,
                                 user=self.user,
                                 password=self.password,
                                 db=self.db,
                                 autocommit=self.autocommit,
                                 pool_recycle=self.pool_recycle)
        self.pool = None

    async def get_pool(self):
        if self.pool and not self.pool._closed:
            return self.pool
        self.pool = await aiomysql.create_pool(**self.connect_args)
        return self.pool

    async def _execute(self,
                       cursor,
                       execute_cmd: str,
                       sql: str,
                       args: typing.Union[list, dict] = None,
                       fetchall: typing.Union[bool, None] = True,
                       cursor_class: aiomysql.Cursor = aiomysql.DictCursor):
        """用来在指定 cursor 对象的时候执行语句"""
        result = await getattr(cursor, execute_cmd)(sql, args)
        logger.info(cursor._executed)
        if fetchall:
            result = await cursor.fetchall()
        elif fetchall is False:
            result = await cursor.fetchone()
        elif fetchall is None:
            result = result
        return result

    async def execute(self,
                      sql: str,
                      args: typing.Union[list, dict] = None,
                      fetchall: typing.Union[bool, None] = True,
                      cursor_class: aiomysql.Cursor = aiomysql.DictCursor,
                      cursor: aiomysql.Cursor = None) -> typing.Any:
        """简单的通过 sql 获取数据.

        :param sql: query 的 sql 语句
        :type sql: str
        :param args: query 语句的参数, defaults to None
        :type args: typing.Union[list, dict], optional
        :param fetchall: 是否全部取出来, 默认为 True, 调用 fetchall; 如果设为 None(默认), 只返回受影响的行数; 如果设为 False, 则调用 fetchone
        :type fetchall: bool, optional
        :param cursor_class: 默认使用字典表示一行数据, defaults to aiomysql.DictCursor
        :type cursor_class: aiomysql.Cursor, optional
        :param cursor: 现成的 cursor, 如果没有指定, 则去连接池里创建
        :type cursor_class: aiomysql.Cursor
        :return: 返回 fetchmany / fetchone 的结果
        :rtype: typing.Any
        """
        if cursor:
            return await self._execute(cursor,
                                       'execute',
                                       sql=sql,
                                       args=args,
                                       fetchall=fetchall,
                                       cursor_class=cursor_class)
        conn_pool = await self.get_pool()
        async with conn_pool.acquire() as conn:
            async with conn.cursor(cursor_class) as cursor:
                return await self._execute(cursor,
                                           'execute',
                                           sql=sql,
                                           args=args,
                                           fetchall=fetchall,
                                           cursor_class=cursor_class)

    async def executemany(self,
                          sql: str,
                          args: list = None,
                          fetchall: typing.Union[bool, None] = True,
                          cursor_class: aiomysql.Cursor = aiomysql.DictCursor,
                          cursor: aiomysql.Cursor = None) -> typing.Any:
        """简单的通过 sql 获取数据.
        
        :param sql: query 的 sql 语句
        :type sql: str
        :param args: query 语句的参数, 只能为 list, defaults to None
        :type args: list, optional
        :param fetchall: 是否全部取出来, 默认为 True, 调用 fetchall; 如果设为 None(默认), 只返回受影响的行数; 如果设为 False, 则调用 fetchone
        :type fetchall: bool, optional
        :param cursor_class: 默认使用字典表示一行数据, defaults to aiomysql.DictCursor
        :type cursor_class: aiomysql.Cursor, optional
        :return: 返回 fetchmany / fetchone 的结果
        :rtype: typing.Any
        """
        if cursor:
            return await self._execute(cursor,
                                       'executemany',
                                       sql=sql,
                                       args=args,
                                       fetchall=fetchall,
                                       cursor_class=cursor_class)
        conn_pool = await self.get_pool()
        async with conn_pool.acquire() as conn:
            async with conn.cursor(cursor_class) as cursor:
                return await self._execute(cursor,
                                           'executemany',
                                           sql=sql,
                                           args=args,
                                           fetchall=fetchall,
                                           cursor_class=cursor_class)

    async def _ensure_article_table_exists(self):
        is_exists = await self.execute(
            "SELECT table_name FROM information_schema.TABLES WHERE table_name ='articles'",
            fetchall=False)
        if is_exists:
            logger.info('`articles` table exists.')
            return
        logger.info('start creating `articles` table.')
        sql = '''CREATE TABLE if not exists `articles` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `url_key` char(32) NOT NULL COMMENT '通过 url 计算的 md5',
  `title` varchar(128) NOT NULL DEFAULT '无题' COMMENT '文章标题',
  `url` varchar(255) NOT NULL COMMENT '文章地址',
  `cover` varchar(255) NOT NULL DEFAULT '' COMMENT '文章封面图片',
  `desc` text COMMENT '文章描述, 如果是周报, 则包含所有文字',
  `source` varchar(32) NOT NULL DEFAULT '未知' COMMENT '文章来源',
  `level` tinyint(4) NOT NULL COMMENT '来源评分',
  `featured` tinyint(4) NOT NULL DEFAULT '0' COMMENT '是否被推荐',
  `ts_publish` timestamp NOT NULL DEFAULT '2019-04-28 21:30:15' COMMENT '发布时间',
  `ts_create` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `ts_update` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `url_key_index` (`url_key`) USING BTREE,
  KEY `ts_publish_index` (`ts_publish`) USING BTREE,
  FULLTEXT KEY `full_text_index` (`title`,`desc`,`url`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存放文章数据'
'''
        await self.execute(sql, fetchall=None)
        logger.info('`articles` table created.')

    async def add_articles(self, articles: list, cursor=None):
        """事先要注意保证 articles 的 keys 是一样的"""
        old_articles_length = len(articles)
        articles = self.ensure_articles(articles)
        if not articles:
            return
        # 拿到第一个 article 的 keys 拼凑 sql
        keys = ', '.join([f'`{key}`' for key in articles[0].keys()])
        value_keys = ','.join([f'%({key})s' for key in articles[0].keys()])
        sql = f'''insert ignore into `articles` ({keys}) values ({value_keys})'''
        result = await self.executemany(sql,
                                        articles,
                                        fetchall=None,
                                        cursor=cursor)
        source = articles[0]['source']
        logger.info(
            f'[{source}]: crawled {old_articles_length} articles, inserted {result}.'
        )
        return result

    async def del_articles(self, *args, **kwargs):
        raise NotImplementedError

    async def update_articles(self, *args, **kwargs):
        raise NotImplementedError

    async def query_articles(self,
                             query: str = None,
                             start_time: str = "",
                             end_time: str = "",
                             sourse: str = "",
                             order_by: str = 'ts_publish',
                             sorting: str = 'desc',
                             limit: int = 10,
                             offset: int = 0):
        args = []
        where_list = []
        result = {}
        limit = min((self.max_limit, int(limit)))
        offset = int(offset)
        order_by = order_by.strip(' `')
        if order_by not in self.articles_table_columns:
            order_by = 'ts_publish'
        if sorting.lower() not in ('desc', 'asc'):
            sorting = 'desc'
        if start_time:
            where_list.append("`ts_publish` >= %s")
            args.append(start_time)
            result['start_time'] = start_time
        if end_time:
            where_list.append("`ts_publish` <= %s")
            args.append(end_time)
            result['end_time'] = end_time
        if sourse:
            where_list.append("`sourse` = %s")
            args.append(sourse)
            result['sourse'] = sourse
        if query:
            where_list.append("MATCH(`title`, `desc`, `url`) AGAINST(%s)")
            args.append(query)
        result['order_by'] = order_by
        result['sorting'] = sorting
        result['limit'] = limit
        result['offset'] = offset
        args.extend([limit + 1, offset])
        if where_list:
            where_string = 'where ' ' and '.join(where_list)
        else:
            where_string = ''
        sql = f"SELECT * from articles {where_string} order by {order_by} {sorting} limit %s offset %s"
        logger.info(f'fetching articles sql: {sql}, args: {args}')
        items = await self.execute(sql, args)
        result['has_more'] = 1 if len(items) > limit else 0
        articles = self.format_output_articles(items[:limit])
        result['articles'] = articles
        return result


class Sqlite3Storage(Storage):
    """本地数据库, 主要用来备份线上数据避免阿里云翻车或者迁移的时候用."""


class MongoDBStorage(Storage):
    """连接免费的 mongolab 数据库, 之后迁移到 heroku 的时候使用它."""
