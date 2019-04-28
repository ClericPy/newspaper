import abc

import aiomysql

from .config import db_instance, global_configs


class Storage(object, metaclass=abc.ABCMeta):
    """存储器抽象. 统一参数对文章数据库进行增删改查."""

    def __init__(self, *args, **kwargs):
        self.ensure_table()

    @abc.abstractmethod
    def ensure_table(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def add_article(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def del_article(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def update_article(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def query_article(self, *args, **kwargs):
        raise NotImplementedError


class MySQLStorage(Storage):
    """连接 mysql 线上数据库"""
    create_table_sql = '''CREATE TABLE `articles` (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'''

    def __init__(self):
        self.host = global_configs['mysql_host']
        self.port = global_configs['mysql_port']
        self.user = global_configs['mysql_user']
        self.password = global_configs['mysql_password']
        self.db = global_configs['mysql_db']

    def ensure_table(self, *args, **kwargs):
        raise NotImplementedError

    def add_article(self, *args, **kwargs):
        raise NotImplementedError

    def del_article(self, *args, **kwargs):
        raise NotImplementedError

    def update_article(self, *args, **kwargs):
        raise NotImplementedError

    def query_article(self, *args, **kwargs):
        raise NotImplementedError


class Sqlite3Storage(Storage):
    """本地数据库, 主要用来备份线上数据避免阿里云翻车或者迁移的时候用."""

    # TODO

    def ensure_table(self, *args, **kwargs):
        raise NotImplementedError

    def add_article(self, *args, **kwargs):
        raise NotImplementedError

    def del_article(self, *args, **kwargs):
        raise NotImplementedError

    def update_article(self, *args, **kwargs):
        raise NotImplementedError

    def query_article(self, *args, **kwargs):
        raise NotImplementedError


class MongoDBStorage(Storage):
    """连接免费的 mongolab 数据库, 之后迁移到 heroku 的时候使用它."""
    # TODO

    def ensure_table(self, *args, **kwargs):
        raise NotImplementedError

    def add_article(self, *args, **kwargs):
        raise NotImplementedError

    def del_article(self, *args, **kwargs):
        raise NotImplementedError

    def update_article(self, *args, **kwargs):
        raise NotImplementedError

    def query_article(self, *args, **kwargs):
        raise NotImplementedError


def choose_db(db_instance: str):
    """根据 config 的 db_instance 确定要使用什么数据库

    :param db_instance: 数据库类型
    :type db_instance: str
    :raises RuntimeError: 如果没有存储器, 则直接报错无法执行
    """
    if db_instance == 'mysql':
        db = MySQLStorage()
    elif db_instance == 'sqlite':
        db = Sqlite3Storage()
    elif db_instance == 'mongodb':
        db = MongoDBStorage()
    else:
        raise RuntimeError('bad db_instance %s' % db_instance)
    return db


db = choose_db(db_instance=db_instance)
