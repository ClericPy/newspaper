import abc
import asyncio
import typing

import aiomysql
from torequests.utils import json, md5

from .config import global_configs


class Storage(object, metaclass=abc.ABCMeta):
    """存储器抽象. 统一参数对文章数据库进行增删改查."""

    def __init__(self, *args, **kwargs):
        self.ensure_table()

    @abc.abstractmethod
    async def ensure_table(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def add_article(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def del_article(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def update_article(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def query_article(self, *args, **kwargs):
        raise NotImplementedError


class MySQLStorage(Storage):
    """连接 mysql 线上数据库, 目前不需要读写分离, 因为只初始化一次, 所以不需要单例.

    example::

        
    """

    def __init__(self, mysql_config):
        self.host = mysql_config['mysql_host']
        self.port = mysql_config['mysql_port']
        self.user = mysql_config['mysql_user']
        self.password = mysql_config['mysql_password']
        self.db = mysql_config['mysql_db']
        self.connect_args = dict(host=self.host,
                                 port=self.port,
                                 user=self.user,
                                 password=self.password,
                                 db=self.db,
                                 loop=asyncio.get_event_loop())
        self.pool = None

    async def get_pool(self):
        if self.pool and not self.pool._closed:
            return self.pool
        self.pool = await aiomysql.create_pool(**self.connect_args)
        return self.pool

    async def execute(self,
                      sql: str,
                      args: typing.Union[list, dict] = None,
                      fetchall: bool = True,
                      cursor_class: aiomysql.Cursor = aiomysql.DictCursor
                     ) -> typing.Any:
        """简单的通过 sql 获取数据.
        
        :param sql: query 的 sql 语句
        :type sql: str
        :param args: query 语句的参数, defaults to None
        :type args: typing.Union[list, dict], optional
        :param fetchall: 是否全部取出来, 默认为 True, 调用 fetchall; 如果设为 None(默认), 只返回受影响的行数; 如果设为 False, 则调用 fetchone
        :type fetchall: bool, optional
        :param cursor_class: 默认使用字典表示一行数据, defaults to aiomysql.DictCursor
        :type cursor_class: aiomysql.Cursor, optional
        :return: 返回 fetchmany / fetchone 的结果
        :rtype: typing.Any
        """
        conn_pool = await self.get_pool()
        async with conn_pool.acquire() as conn:
            async with conn.cursor(cursor_class) as cur:
                result = await cur.execute('desc articles', args)
                if fetchall:
                    return await cur.fetchall()
                elif fetchall is False:
                    return await cur.fetchone()
                elif fetchall is None:
                    return result

    async def executemany(self,
                          sql: str,
                          args: list = None,
                          fetchall: bool = True,
                          cursor_class: aiomysql.Cursor = aiomysql.DictCursor
                         ) -> typing.Any:
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
        conn_pool = await self.get_pool()
        async with conn_pool.acquire() as conn:
            async with conn.cursor(cursor_class) as cur:
                result = await cur.execute('desc articles', args)
                if fetchall:
                    return await cur.fetchall()
                elif fetchall is False:
                    return await cur.fetchone()
                elif fetchall is None:
                    return result

    @property
    def create_article_table_sql(self):
        return '''CREATE TABLE `articles` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `key` char(32) CHARACTER SET latin1 NOT NULL COMMENT '通过 url 计算的 md5',
  `title` varchar(128) NOT NULL DEFAULT '无题' COMMENT '文章标题',
  `cover` varchar(255) DEFAULT NULL COMMENT '文章封面图片',
  `desc` text NOT NULL COMMENT '文章描述, 如果是周报, 则包含所有文字',
  `source` varchar(32) NOT NULL DEFAULT '未知' COMMENT '文章来源',
  `score` tinyint(4) NOT NULL COMMENT '来源评分',
  `featured` tinyint(4) NOT NULL DEFAULT '0' COMMENT '是否被推荐',
  `ts_publish` timestamp NOT NULL DEFAULT '2019-04-28 21:30:15' COMMENT '发布时间',
  `ts_create` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `ts_update` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `key` (`key`),
  KEY `create_index` (`ts_create`),
  FULLTEXT KEY `full_text_index` (`title`,`desc`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存放文章数据'
'''

    def ensure_table(self, *args, **kwargs):
        """判断是否 db 里有 articles 表, 如果没有, 创建它"""
        raise NotImplementedError

    async def add_article(self, *args, **kwargs):
        raise NotImplementedError

    async def del_article(self, *args, **kwargs):
        raise NotImplementedError

    async def update_article(self, *args, **kwargs):
        raise NotImplementedError

    async def query_article(self, *args, **kwargs):
        raise NotImplementedError


class Sqlite3Storage(Storage):
    """本地数据库, 主要用来备份线上数据避免阿里云翻车或者迁移的时候用."""

    # TODO
    async def ensure_table(self, *args, **kwargs):
        raise NotImplementedError

    async def add_article(self, *args, **kwargs):
        raise NotImplementedError

    async def del_article(self, *args, **kwargs):
        raise NotImplementedError

    async def update_article(self, *args, **kwargs):
        raise NotImplementedError

    async def query_article(self, *args, **kwargs):
        raise NotImplementedError


class MongoDBStorage(Storage):
    """连接免费的 mongolab 数据库, 之后迁移到 heroku 的时候使用它."""

    # TODO
    async def ensure_table(self, *args, **kwargs):
        raise NotImplementedError

    async def add_article(self, *args, **kwargs):
        raise NotImplementedError

    async def del_article(self, *args, **kwargs):
        raise NotImplementedError

    async def update_article(self, *args, **kwargs):
        raise NotImplementedError

    async def query_article(self, *args, **kwargs):
        raise NotImplementedError
