import abc
import re
import sqlite3
import typing
import warnings
from datetime import datetime

import aiomysql
from async_lru import alru_cache
from torequests.utils import ptime, time, ttime

from .loggers import logger
from .crawler.sources import content_sources_dict

# 用了 insert ignore 还总是 warning, 又不想 insert try, 只好全禁掉了...
warnings.filterwarnings('ignore', category=aiomysql.Warning)


class Storage(object, metaclass=abc.ABCMeta):
    """存储器抽象. 统一参数对文章数据库进行增删改查."""
    max_limit = 100  # 避免 limit 设置的太大一次提取太多导致拥堵
    articles_table_columns = ('url_key', 'title', 'url', 'cover', 'desc',
                              'source', 'level', 'review', 'ts_publish',
                              'ts_create', 'ts_update')

    def format_output_articles(self, articles: typing.Sequence[dict]):
        for article in articles:
            for key, value in article.items():
                if isinstance(value, datetime):
                    article[key] = str(value)
        return articles

    @staticmethod
    def ensure_articles(articles: typing.Sequence[dict]) -> list:
        valid_articles = []
        # ensure_keys = ("url_key", "title", "cover", "desc", "source",
        #                "review", "ts_publish", "lang")
        keys_set = None
        now = ttime()
        today_0_0 = f'{now[:10]} 00:00:00'
        before_3_day_0_0 = f'{ttime(time.time() - 86400*3)[:10]} 00:00:00'
        for article in articles:
            if not isinstance(article, dict):
                continue
            if not keys_set:
                keys_set = set(article.keys())
            else:
                # 如果 keys 和第一个不一样, 就没法使用 executemany, 所以跳过
                if set(article.keys()) != keys_set:
                    continue
            # 这些 key 必须都存在才能入库
            source = content_sources_dict.get(article['source'])
            if not source:
                continue
            for ensure_key in ('url_key', 'title'):
                if not article.get(ensure_key):
                    continue
            article.setdefault('cover', '')
            article.setdefault('desc', '')
            article.setdefault('source', 'unknown')
            article.setdefault('review', '')
            article.setdefault('level', source.get('level', 3))
            article.setdefault('lang', source.get('lang', 'CN'))
            article.setdefault('ts_publish', '1970-01-01 08:00:01')
            article['desc'] = re.sub(
                r'<script[\s\S]*?</script>|<style[\s\S]*?</style>', '',
                article['desc']).strip()
            article['title'] = article['title'].strip()
            # mysql 会报错 0000-00-00 00:00:00 格式错误; 顺便尝试转换掉错误的发布时间
            if ttime(ptime(article['ts_publish'])) == '1970-01-01 08:00:00':
                article['ts_publish'] = '1970-01-01 08:00:01'
            if not article.get('ts_create'):
                # 最近 3 天发布的, 使用当前时间做抓取时间
                # 如果发布时间不存在, 也使用当前时间做抓取时间
                if article['ts_publish'] >= before_3_day_0_0 or article[
                        'ts_publish'] == '1970-01-01 08:00:01':
                    article['ts_create'] = now
                else:
                    # 不是 3 天内发布的, 使用发布时间做抓取时间
                    article['ts_create'] = article['ts_publish']
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
        self.pool_recycle = 600
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
        if isinstance(cursor._executed, str):
            # 有时候是 bytesarray, 没什么必要看
            logger.info(f'[Execute SQL]: {cursor._executed[:256]}')
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
        logger.info('start creating `articles` table for table missing.')
        #! 每次修改这里要确定好和下面的 sqlite 部分是一致的
        sql = '''CREATE TABLE `articles` (
  `url_key` char(32) NOT NULL COMMENT '通过 url 计算的 md5',
  `title` varchar(128) NOT NULL DEFAULT '无题' COMMENT '文章标题',
  `url` varchar(255) NOT NULL COMMENT '文章地址',
  `cover` varchar(255) NOT NULL DEFAULT '' COMMENT '文章封面图片',
  `desc` text COMMENT '文章描述, 如果是周报, 则包含所有文字',
  `source` varchar(32) NOT NULL DEFAULT '未知' COMMENT '文章来源',
  `level` tinyint(4) NOT NULL COMMENT '来源评分',
  `lang` char(2) DEFAULT NULL COMMENT '语言类型 cn, en',
  `review` varchar(255) NOT NULL DEFAULT '' COMMENT '点评评语',
  `ts_publish` timestamp NOT NULL DEFAULT '1970-01-01 08:00:01' COMMENT '发布时间',
  `ts_create` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `ts_update` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`url_key`),
  KEY `ts_create_index` (`ts_create`) USING BTREE,
  KEY `ts_publish_index` (`ts_publish`),
  FULLTEXT KEY `full_text_index` (`title`,`desc`,`url`) /*!50100 WITH PARSER `ngram` */ 
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存放文章数据.'
'''
        await self.execute(sql, fetchall=None)
        logger.info('`articles` table created.')

    async def add_articles(self, articles, cursor=None):
        """事先要注意保证 articles list 的每个 dict keys 是一样的"""
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
        if result:
            logger.info(
                f'[{source}]: crawled {old_articles_length} articles, inserted {result}.'
            )
        return result

    async def del_articles(self, *args, **kwargs):
        raise NotImplementedError

    async def update_articles(self, *args, **kwargs):
        raise NotImplementedError

    @alru_cache(maxsize=10)
    async def query_articles(
            self,
            query: str = None,
            start_time: str = "",
            end_time: str = "",
            source: str = "",
            order_by: str = 'ts_create',
            sorting: str = 'desc',
            limit: int = 30,
            offset: int = 0,
            date: str = '',
            lang: str = 'ANY',
    ) -> dict:
        args: list = []
        where_list: list = []
        result: dict = {}
        source = str(source)
        order_by = order_by.strip(' `')
        limit = min((self.max_limit, int(limit)))
        offset = int(offset)
        lang = str(lang).upper()
        extra_select_words: str = ''

        if query:
            # 带检索词的，添加上字段方便排序
            extra_select_words = ', MATCH (`title`, `desc`, `url`) AGAINST (%s IN BOOLEAN MODE)  as relevance'
            args.append(query)
            where_list.append(
                'MATCH (`title`, `desc`, `url`) AGAINST (%s in BOOLEAN MODE)')
            args.append(query)
        if order_by not in self.articles_table_columns and order_by != 'relevance':
            order_by = 'ts_create'
        order_by_sorting = f'order by {order_by} {sorting}'
        if date:
            if date == 'today':
                date = ttime()[:10]
            elif date == 'yesterday':
                date = ttime(time.time() - 86400)[:10]
            # 将 date 换算成起止时间并覆盖
            date = str(date)
            if not re.match('\\d\\d\\d\\d-\\d\\d-\\d\\d', date):
                raise ValueError(f'日期参数的格式不对 {date}, 例: 2019-05-14')
            start_time = f'{date} 00:00:00'
            end_time = f'{date} 23:59:59'
            limit = 9999
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
        if source:
            where_list.append("`source` = %s")
            args.append(source)
            result['source'] = source

        if lang in {'CN', 'EN'}:
            where_list.append("`lang` = %s")
            args.append(lang)
        else:
            lang = 'ANY'

        result['order_by'] = order_by
        result['query'] = query or ''
        result['sorting'] = sorting
        result['limit'] = limit
        result['offset'] = offset
        result['date'] = date
        args.extend([limit + 1, offset])
        if where_list:
            where_string = 'where ' + ' and '.join(where_list)
        else:
            where_string = ''
        sql = f"SELECT *{extra_select_words} from articles {where_string} {order_by_sorting} limit %s offset %s"
        logger.info(f'fetching articles sql: {sql}, args: {args}')
        items = await self.execute(sql, args)
        result['has_more'] = 1 if len(items) > limit else 0
        articles = self.format_output_articles(items[:limit])
        result['articles'] = articles
        result['lang'] = lang
        return result


class Sqlite3Storage(Storage):
    """本地数据库, 主要用来备份线上数据避免阿里云翻车或者迁移的时候用."""

    def __init__(self, file_path):
        self.db = sqlite3.connect(file_path)
        self.cursor = self.db.cursor()

    def __del__(self):
        self.db.close()

    def add_articles(self, articles):
        articles = self.ensure_articles(articles)
        if not articles:
            return
        for article in articles:
            keys = list(article.keys())
            keys_str = ', '.join([f'`{key}`' for key in keys])
            values = [article[key] for key in keys]
            value_keys = ','.join([f'?' for key in keys])
            sql = f'''insert or ignore into `articles` ({keys_str}) values ({value_keys})'''
            result = self.cursor.execute(sql, values)
        self.db.commit()
        return result

    def del_articles(self, *args, **kwargs):
        pass

    def update_articles(self, *args, **kwargs):
        pass

    def query_articles(self, *args, **kwargs):
        pass

    def _ensure_article_table_exists(self):
        self.cursor.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='articles'"
        )
        is_exists = bool(self.cursor.fetchone()[0])
        if is_exists:
            logger.info('`articles` table exists. [sqlite]')
            return
        logger.info(
            'start creating `articles` table for table missing. [sqlite]')
        #! sqlite 只用来备份, 所以不建索引, 不支持 mysql 的 ENGINE, INDEX, COMMENT
        self.cursor.execute("""CREATE TABLE `articles` (
`url_key` char(32) NOT NULL ,
`title` varchar(128) NOT NULL DEFAULT '无题' ,
`url` varchar(255) NOT NULL ,
`cover` varchar(255) NOT NULL DEFAULT '' ,
`desc` text ,
`source` varchar(32) NOT NULL DEFAULT '未知' ,
`level` tinyint(4) NOT NULL ,
`lang` char(2) DEFAULT NULL ,
`review` varchar(255) NOT NULL DEFAULT '' ,
`ts_publish` timestamp NOT NULL DEFAULT '1970-01-01 08:00:01' ,
`ts_create` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ,
`ts_update` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
PRIMARY KEY (`url_key`)
)""")


class MongoDBStorage(Storage):
    """连接免费的 mongolab 数据库, 之后迁移到 heroku + mlab(免费 mongodb) 的时候使用它."""
