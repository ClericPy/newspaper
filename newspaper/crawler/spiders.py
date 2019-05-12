import asyncio
import json
import traceback
import typing
import zlib
from functools import wraps

from lxml.html import fromstring
from torequests.dummy import Requests
from torequests.utils import ptime, ttime, md5, time

from ..config import spider_logger as logger, global_configs
from .sources import content_sources_dict

online_spiders = []
history_spiders = []
req = Requests()


class null_tree:
    text = ''

    @classmethod
    def text_content(cls):
        return ''


def get_url_key(url: str) -> str:
    """通过 url 来计算 key, 一方面计算 md5, 另一方面净化无用参数.
    以后再考虑要不要纯数字...
    import hashlib
    a = hashlib.md5(b'url')
    b = a.hexdigest()
    as_int = int(b, 16)
    url_key = str(as_int)[5:][:20]
    print(url_key)
"""
    return md5(url)


async def outlands_request(request_dict: dict, encoding: str = 'u8') -> str:
    """小水管不开源, 无法用来 FQ.

    例:
        async def test():
            text = await outlands_request({
                'method': 'get',
                'url': 'https://pyfound.blogspot.com/'
            }, 'u8')
            print(text)
            return text
    """
    data = json.dumps(request_dict)
    data = zlib.compress(data.encode('u8'))
    url = global_configs['anti_gfw']['url']
    r = await req.post(url, timeout=60, data=data)
    if r:
        return zlib.decompress(r.content).decode(encoding)
    else:
        return r.text


def register_online(function: typing.Callable) -> typing.Callable:
    """把爬虫注册到线上可用列表

    :param function: 爬虫函数, 一般没有参数.
    :type function: typing.Callable
    :return: 爬虫函数, 一般没有参数.
    :rtype: typing.Callable
    """

    online_spiders.append(function)
    return function


def register_history(function: typing.Callable) -> typing.Callable:
    """把爬虫注册到历史文章抓取任务列表

    :param function: 爬虫函数, 一般没有参数.
    :type function: typing.Callable
    :return: 爬虫函数, 一般没有参数.
    :rtype: typing.Callable
    """

    history_spiders.append(function)
    return function


@register_online
async def python_news() -> list:
    """Python Software Foundation News"""
    source = 'Python Software Foundation News'
    articles = []
    seed = 'https://pyfound.blogspot.com/search?max-results=10'
    scode = await outlands_request({
        'method': 'get',
        'url': seed,
    }, 'u8')
    if scode:
        tree = fromstring(scode)
        for item in tree.cssselect('.blog-posts>.date-outer'):
            try:
                article = {
                    'source': source,
                    'level': content_sources_dict[
                        'Python Software Foundation News']['level']
                }
                raw_pub_time = item.cssselect('.published')[0].get('title', '')
                ts_publish = ttime(
                    ptime(raw_pub_time, fmt='%Y-%m-%dT%H:%M:%S%z'))
                article['ts_publish'] = ts_publish
                article['title'] = item.cssselect(
                    '.post-title.entry-title>a')[0].text
                # 兼容下没有 desc 的情况
                desc = (item.cssselect('.post-body.entry-content') or
                        [null_tree])[0].text_content()
                article['desc'] = desc.split('\n\n\n',
                                             1)[0].strip().replace('\n', ' ')
                article['url'] = item.cssselect(
                    '.post-title.entry-title>a')[0].get('href', '')
                article['url_key'] = get_url_key(article['url'])
                articles.append(article)
            except Exception:
                logger.error('python_news_history crawl failed: %s' %
                             traceback.format_exc())
    logger.info(f'[{source}]: crawled {len(articles)} articles')
    return articles


# @register_history
async def python_news_history() -> list:
    """Python Software Foundation News"""
    source = 'Python Software Foundation News'
    articles = []
    current_year = int(time.strftime('%Y'))
    for year in range(2006, current_year + 1):
        seed = f'https://pyfound.blogspot.com/{year}/'
        scode = await outlands_request({
            'method': 'get',
            'url': seed,
        }, 'u8')
        await asyncio.sleep(3)
        if not scode:
            continue
        tree = fromstring(scode)
        for item in tree.cssselect('.blog-posts>.date-outer'):
            try:
                article = {
                    'source': source,
                    'level': content_sources_dict[
                        'Python Software Foundation News']['level']
                }
                raw_pub_time = item.cssselect('.published')[0].get('title', '')
                ts_publish = ttime(
                    ptime(raw_pub_time, fmt='%Y-%m-%dT%H:%M:%S%z'))
                article['ts_publish'] = ts_publish
                article['title'] = item.cssselect(
                    '.post-title.entry-title>a')[0].text
                # 兼容下没有 desc 的情况
                desc = (item.cssselect('.post-body.entry-content') or
                        [null_tree])[0].text_content()
                article['desc'] = desc.split('\n\n\n',
                                             1)[0].strip().replace('\n', ' ')
                article['url'] = item.cssselect(
                    '.post-title.entry-title>a')[0].get('href', '')
                article['url_key'] = get_url_key(article['url'])
                articles.append(article)
            except Exception:
                logger.error('python_news_history crawl failed: %s' %
                             traceback.format_exc())
    logger.info(f'[{source}]: crawled {len(articles)} articles')
    return articles
