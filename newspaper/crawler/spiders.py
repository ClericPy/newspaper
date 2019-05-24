import asyncio
import json
import traceback
import typing
import zlib

from lxml.html import fromstring, tostring
from torequests.dummy import Requests
from torequests.utils import (find_one, md5, parse_qsl, ptime, re, time, ttime,
                              unparse_qsl, urlparse, urlunparse)

from ..config import global_configs
from ..config import spider_logger as logger
from .sources import content_sources_dict

test_spiders = []
online_spiders = []
history_spiders = []
req = Requests()
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36'


class null_tree:
    text = ''

    @classmethod
    def text_content(cls):
        return ''


def sort_url_query(url, reverse=False, _replace_kwargs=None):
    """sort url query args.
    _replace_kwargs is a dict to update attributes before sorting  (such as scheme / netloc...).
    http://www.google.com?b=2&z=26&a=1 => http://www.google.com?a=1&b=2&z=26
    """
    parsed = urlparse(url)
    if _replace_kwargs:
        parsed = parsed._replace(**_replace_kwargs)
    sorted_parsed = parsed._replace(
        query=unparse_qsl(parse_qsl(parsed.query), sort=True, reverse=reverse))
    return urlunparse(sorted_parsed)


def get_url_key(url) -> str:
    """通过 url 来计算 key, 一方面计算 md5, 另一方面净化无用参数.
    以后再考虑要不要纯数字...
    import hashlib
    a = hashlib.md5(b'url')
    b = a.hexdigest()
    as_int = int(b, 16)
    url_key = str(as_int)[5:][:20]
    print(url_key)
"""
    if url:
        key = md5(sort_url_query(url, _replace_kwargs={'scheme': 'https'}))
        return key
    return ""


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
    if not request_dict.get('headers', {}).get('User-Agent'):
        request_dict.setdefault('headers', {})
        request_dict['headers'][
            'User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36'
    json_data = json.dumps(request_dict)
    data = zlib.compress(json_data.encode('u8'))
    url = global_configs['anti_gfw']['url']
    r = await req.post(url, timeout=60, data=data)
    if r:
        return zlib.decompress(r.content).decode(encoding)
    else:
        return r.text


def register_test(function: typing.Callable) -> typing.Callable:
    """把爬虫注册到测试列表

    :param function: 爬虫函数, 一般没有参数.
    :type function: typing.Callable
    :return: 爬虫函数, 一般没有参数.
    :rtype: typing.Callable
    """

    test_spiders.append(function)
    return function


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
    articles: list = []
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
                    'level': content_sources_dict[source]['level']
                }
                raw_pub_time = item.cssselect('.published')[0].get('title', '')
                ts_publish = ttime(
                    ptime(raw_pub_time, fmt='%Y-%m-%dT%H:%M:%S%z'))
                article['ts_publish'] = ts_publish
                article['title'] = item.cssselect(
                    '.post-title.entry-title>a')[0].text
                # 兼容下没有 desc 的情况
                node = item.cssselect('.post-body.entry-content') or [null_tree]
                desc = node[0].text_content()
                article['desc'] = desc.split('\n\n\n',
                                             1)[0].strip().replace('\n', ' ')
                article['url'] = item.cssselect(
                    '.post-title.entry-title>a')[0].get('href', '')
                article['url_key'] = get_url_key(article['url'])
                articles.append(article)
            except Exception:
                logger.error(f'{source} crawl failed: {traceback.format_exc()}')
    logger.info(f'crawled {len(articles)} articles [{source}]')
    return articles


# @register_history
async def python_news_history() -> list:
    """Python Software Foundation News"""
    source = 'Python Software Foundation News'
    articles: list = []
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
                    'level': content_sources_dict[source]['level']
                }
                raw_pub_time = item.cssselect('.published')[0].get('title', '')
                ts_publish = ttime(
                    ptime(raw_pub_time, fmt='%Y-%m-%dT%H:%M:%S%z'))
                article['ts_publish'] = ts_publish
                article['title'] = item.cssselect(
                    '.post-title.entry-title>a')[0].text
                # 兼容下没有 desc 的情况
                node = item.cssselect('.post-body.entry-content') or [null_tree]
                desc = node[0].text_content()
                article['desc'] = desc.split('\n\n\n',
                                             1)[0].strip().replace('\n', ' ')
                article['url'] = item.cssselect(
                    '.post-title.entry-title>a')[0].get('href', '')
                article['url_key'] = get_url_key(article['url'])
                articles.append(article)
            except Exception:
                logger.error(f'{source} crawl failed: {traceback.format_exc()}')
    logger.info(f'crawled {len(articles)} articles [{source}]')
    return articles


def _python_weekly_calculate_date(issue_id):
    diff = 396 - int(issue_id)
    return ttime(1557331200 - diff * 86400 * 7)


@register_online
async def python_weekly() -> list:
    """Python Weekly"""
    source = 'Python Weekly'
    articles: list = []
    # 一周一更, 所以只取第一个就可以了
    limit = 1
    seed = 'https://us2.campaign-archive.com/home/?u=e2e180baf855ac797ef407fc7&id=9e26887fc5'
    scode = await outlands_request({
        'method': 'get',
        'url': seed,
    }, 'u8')
    box = find_one(
        r'(?:<div class="display_archive">)(<li [\s\S]*?</li>)(?:</div>)',
        scode)[1]
    items = re.findall(r'(<li [\s\S]*?</li>)', box)
    for item in items[:limit]:
        try:
            article = {
                'source': source,
                'level': content_sources_dict[source]['level']
            }
            # 从列表页取 ts_publish 和 issue_id, 其他的去详情页里采集
            # <li class="campaign">05/09/2019 - <a href="http://eepurl.com/gqB4vv" title="Python Weekly - Issue 396" target="_blank">Python Weekly - Issue 396</a></li>
            title = find_one('title="(.*?)"', item)[1]
            issue_id = find_one(r' - Issue (\d+)', title)[1]
            pub_dates = find_one(r'class="campaign">(\d\d)/(\d\d)/(\d\d\d\d)',
                                 item)[1]
            if not issue_id:
                continue
            if len(pub_dates) == 3:
                ts_publish = f'{pub_dates[2]}-{pub_dates[0]}-{pub_dates[1]} 00:00:00'
            else:
                ts_publish = _python_weekly_calculate_date(issue_id)
            article['ts_publish'] = ts_publish
            detail_url = f'https://mailchi.mp/pythonweekly/python-weekly-issue-{issue_id}'
            r = await req.get(
                detail_url,
                verify=0,
                headers={
                    "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36'
                })
            if not r:
                logger.error(f'fetch {detail_url} failed: {r}')
                continue
            scode = r.text
            title = find_one('<title>(.*?)</title>', r.text)[1]
            title = title.strip('Â ')
            translate_url = find_one(
                r'(://translate\.google\.com/translate\?[^"]+)', scode)[1]
            backup_url = dict(
                parse_qsl(translate_url))['u'] if translate_url else ''
            backup_url_desc = f'<a href="{backup_url}" target="_blank" rel="noopener noreferrer"><b>View this email in your browser</b></a><br>' if backup_url else ''
            nodes = fromstring(scode).cssselect('[style="font-size:14px"]>a')
            all_links = [
                f"「{tostring(i, method='html', with_tail=0, encoding='unicode')} 」"
                for i in nodes
            ]
            all_links_desc = '<br>'.join(all_links)
            article['title'] = title
            article['desc'] = f'{backup_url_desc}{all_links_desc}'
            article['url'] = detail_url
            article['url_key'] = get_url_key(article['url'])
            articles.append(article)
        except Exception:
            logger.error(f'{source} crawl failed: {traceback.format_exc()}')
            break
    logger.info(f'crawled {len(articles)} articles [{source}]')
    return articles


# @register_history
async def python_weekly_history() -> list:
    """Python Weekly"""
    source = 'Python Weekly'
    articles: list = []
    for issue_id in range(324, 1000):
        try:
            article = {
                'source': source,
                'level': content_sources_dict[source]['level']
            }
            article['ts_publish'] = _python_weekly_calculate_date(issue_id)
            detail_url = f'https://mailchi.mp/pythonweekly/python-weekly-issue-{issue_id}'
            r = await req.get(
                detail_url,
                verify=0,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36'
                })
            if '<title>404: Page Not Found' in r.text:
                logger.warn('python_weekly_history break for 404 page')
                break
            if not r:
                logger.error(f'python_weekly_history break for {r}')
                break
            scode = r.text
            title = find_one('<title>(.*?)</title>', r.text)[1]
            title = title.strip('Â ')
            translate_url = find_one(
                r'(://translate\.google\.com/translate\?[^"]+)', scode)[1]
            backup_url = dict(
                parse_qsl(translate_url))['u'] if translate_url else ''
            backup_url_desc = f'<a href="{backup_url}" target="_blank" rel="noopener noreferrer"><b>View this email in your browser</b></a><br>' if backup_url else ''
            nodes = fromstring(scode).cssselect('[style="font-size:14px"]>a')
            all_links = [
                f"「{tostring(i, method='html', with_tail=0, encoding='unicode')} 」"
                for i in nodes
            ]
            all_links_desc = '<br>'.join(all_links)
            article['title'] = title
            article['desc'] = f'{backup_url_desc}{all_links_desc}'
            article['url'] = detail_url
            article['url_key'] = get_url_key(article['url'])
            articles.append(article)
        except Exception:
            logger.error(f'{source} crawl failed: {traceback.format_exc()}')
            break
    logger.info(f'crawled {len(articles)} articles [{source}]')
    return articles


@register_online
async def pycoder_weekly() -> list:
    """PyCoder's Weekly. 把 limit 改 999 就可以抓历史了"""
    source = "PyCoder's Weekly"
    articles: list = []
    # 一周一更, 所以只取第一个就可以了
    limit = 1
    seed = 'https://pycoders.com/issues'
    base_url = find_one('^https?://[^/]+', seed)[0]
    r = await req.get(seed, headers={'User-Agent': UA})
    if not r:
        logger.error(f'{source} crawl failed: {r}, {r.text}')
        return articles
    items = re.findall(r'<a href="/issues/\d+">Issue #\d+ .*?</a>', r.text)
    for item in items[:limit]:
        try:
            article = {
                'source': source,
                'level': content_sources_dict[source]['level']
            }
            # <a href="/issues/368">Issue #368 (May 14, 2019)</a>
            title = find_one('>(Issue.*?)<', item)[1]
            article['title'] = f"PyCoder's Weekly | {title}"
            month, day, year = re.findall(r'\((.*?) (\d+), (\d+)\)',
                                          article['title'])[0]
            month = month[:3]
            raw_time = f'{year}-{month}-{day}'
            ts_publish = ttime(ptime(raw_time, fmt='%Y-%b-%d'))
            article['ts_publish'] = ts_publish
            article['desc'] = ''
            url = find_one(r'href="(/issues/\d+)"', item)[1]
            article['url'] = base_url + url
            article['url_key'] = get_url_key(article['url'])
            articles.append(article)
        except Exception:
            logger.error(f'{source} crawl failed: {traceback.format_exc()}')
            break
    logger.info(f'crawled {len(articles)} articles [{source}]')
    return articles


@register_online
async def importpython() -> list:
    """Import Python"""
    source = 'Import Python'
    articles: list = []
    # 一周一更, 所以只取第一个就可以了
    limit = 1
    seed = 'https://importpython.com/newsletter/archive/'
    r = await req.get(seed, retry=1, timeout=20, headers={"User-Agent": UA})
    if not r:
        logger.error(f'{source} crawl failed: {r}, {r.text}')
        return articles
    items = fromstring(r.text).cssselect('#tourpackages-carousel>.row>div')
    for item in items[:limit]:
        try:
            article = {
                'source': source,
                'level': content_sources_dict[source]['level']
            }
            href = item.cssselect('div.caption>a')[0].get('href', '')
            if not href:
                continue
            url = re.sub('^/', 'https://importpython.com/', href)
            title = item.cssselect('div.caption>.well-add-card>h4')[0].text
            desc_node = item.cssselect('div.caption>div[class="col-lg-12"]')[0]
            desc = tostring(desc_node,
                            method='html',
                            with_tail=0,
                            encoding='unicode')
            day, month, year = re.findall(r'- (\d+) (\S+) (\d+)', title)[0]
            month = month[:3]
            raw_time = f'{year}-{month}-{day}'
            ts_publish = ttime(ptime(raw_time, fmt='%Y-%b-%d'))
            article['ts_publish'] = ts_publish
            article['url'] = url
            clean_title = re.sub(' - .*', '', title)
            title = f"{source} - {clean_title}"
            article['title'] = title
            article['desc'] = desc.replace('\n                    ', ' ')
            article['url'] = url
            article['url_key'] = get_url_key(article['url'])
            articles.append(article)
        except Exception:
            logger.error(f'{source} crawl failed: {traceback.format_exc()}')
            break
    logger.info(f'crawled {len(articles)} articles [{source}]')
    return articles


@register_online
async def awesome_python() -> list:
    """Awesome Python Newsletter"""
    source = 'Awesome Python Newsletter'
    articles: list = []
    # 一周一更, 所以只取第一个就可以了
    limit = 1
    seed = 'https://python.libhunt.com/newsletter/archive'
    r = await req.get(seed, retry=1, timeout=20, headers={"User-Agent": UA})
    if not r:
        logger.error(f'{source} crawl failed: {r}, {r.text}')
        return articles
    hrefs = re.findall(
        r'<td class="text-right">\s*<a href=\'(/newsletter/\d+)\'>', r.text)
    for href in hrefs[:limit]:
        try:
            article = {
                'source': source,
                'level': content_sources_dict[source]['level']
            }
            url = re.sub('^/', 'https://python.libhunt.com/', href)
            r = await req.get(url,
                              retry=2,
                              timeout=15,
                              headers={"User-Agent": UA})
            if not r:
                logger.error(f'fetch {url} failed: {r}')
                break
            tree = fromstring(r.text)
            raw_title = tree.cssselect('title')[0].text
            title = re.sub(', .*', '', raw_title)
            raw_pub_date = find_one(r', (.*?) \|', raw_title)[1]
            # May 17, 2019
            ts_publish = ttime(ptime(raw_pub_date, fmt='%b %d, %Y'))
            nodes = tree.cssselect(
                'li[class="story row"]>div[class="column"]>a')
            descs = [
                tostring(i, method='html', with_tail=0, encoding='unicode')
                for i in nodes
            ]
            desc = '<br>'.join(descs)
            article['ts_publish'] = ts_publish
            article['url'] = url
            article['title'] = title
            article['desc'] = desc
            article['url'] = url
            article['url_key'] = get_url_key(article['url'])
            articles.append(article)
        except Exception:
            logger.error(f'{source} crawl failed: {traceback.format_exc()}')
            break
    logger.info(f'crawled {len(articles)} articles [{source}]')
    return articles


@register_online
async def real_python() -> list:
    """Real Python"""
    source = 'Real Python'
    articles: list = []
    limit = 20
    seed = 'https://realpython.com/'
    r = await req.get(seed, retry=1, timeout=20, headers={"User-Agent": UA})
    if not r:
        logger.error(f'{source} crawl failed: {r}, {r.text}')
        return articles
    items = fromstring(r.text).cssselect('div[class="card border-0"]')
    for item in items[:limit]:
        try:
            article = {
                'source': source,
                'level': content_sources_dict[source]['level']
            }
            href = item.cssselect('a')[0].get('href', '')
            url = re.sub('^/', 'https://realpython.com/', href)
            title = item.cssselect('h2.card-title')[0].text
            pub_date_node = item.cssselect('.mr-2') or [null_tree]
            raw_pub_date = pub_date_node[0].text
            # May 16, 2019
            ts_publish = ttime(ptime(raw_pub_date, fmt='%b %d, %Y'))
            cover_item = item.cssselect('img.card-img-top')
            if cover_item:
                cover = cover_item[0].get('src', '')
                if cover:
                    article['cover'] = cover
            article['ts_publish'] = ts_publish
            article['url'] = url
            article['title'] = title
            article['desc'] = ''
            article['url'] = url
            article['url_key'] = get_url_key(article['url'])
            articles.append(article)
        except Exception:
            logger.error(f'{source} crawl failed: {traceback.format_exc()}')
            break
    logger.info(f'crawled {len(articles)} articles [{source}]')
    return articles


@register_online
async def planet_python() -> list:
    """Planet Python"""
    source = 'Planet Python'
    articles: list = []
    limit = 100
    seed = 'https://planetpython.org/rss20.xml'
    # 避免超时, 用外部访问
    scode = await outlands_request({
        'method': 'get',
        'url': seed,
    }, 'u8')
    items = fromstring(scode).xpath('//channel/item')
    now = ttime()
    for item in items[:limit]:
        try:
            article = {
                'source': source,
                'level': content_sources_dict[source]['level']
            }
            guid = item.xpath('./guid/text()')
            title = item.xpath('./title/text()')
            description = item.xpath('./description/text()')
            pubDate = item.xpath('./pubdate/text()')
            if not (guid and title):
                continue
            url = guid[0]
            title = title[0]
            if description:
                desc = fromstring(description[0]).text_content()
                # 去掉 <>
                desc = re.sub('<[^>]*>', ' ', desc)
                # 只保留第一个换行前面的
                desc = desc.split('\n', 1)[0]
            else:
                desc = ''
            if pubDate:
                raw_pub_date = pubDate[0]
                # Wed, 22 May 2019 01:47:44 +0000
                raw_pub_date = re.sub('^.*?, ', '', raw_pub_date).strip()
                ts_publish = ttime(
                    ptime(raw_pub_date, fmt='%d %b %Y %H:%M:%S %z'))
            else:
                ts_publish = now
            article['ts_publish'] = ts_publish
            article['url'] = url
            article['title'] = title
            article['desc'] = desc
            article['url'] = url
            article['url_key'] = get_url_key(article['url'])
            articles.append(article)
        except Exception:
            logger.error(f'{source} crawl failed: {traceback.format_exc()}')
            break
    logger.info(f'crawled {len(articles)} articles [{source}]')
    return articles
