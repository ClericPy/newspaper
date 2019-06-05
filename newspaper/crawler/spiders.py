import asyncio
import json
import traceback
import typing
import zlib

from lxml.html import fromstring, tostring
from torequests.dummy import Requests
from torequests.utils import (curlparse, find_one, md5, parse_qsl, ptime, re,
                              time, ttime, unparse_qsl, urlparse, urlunparse)

from ..config import global_configs
from ..config import spider_logger as logger
from .sources import content_sources_dict

test_spiders = []
online_spiders = []
history_spiders = []
friendly_crawling_interval = 1
# default_host_frequency 是默认的单域名并发控制: 每 3 秒一次请求
req = Requests(default_host_frequency=(1, 3))
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36'


class null_tree:
    text = ''

    @classmethod
    def text_content(cls):
        return ''

    def get(self, key, default=''):
        return default


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


def add_host(url, host):
    if not host.endswith('/'):
        host = f'{host}/'
    return re.sub('^/', host, url)


def shorten_desc(desc: str) -> str:
    if not desc:
        return ''
    desc = re.sub(r'(\n|\.\s)[\s\S]+', '', desc.strip())
    desc = re.sub('<[^>]+>', '', desc)
    return desc


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
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
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
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
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
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
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
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
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
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
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
            url = add_host(href, 'https://importpython.com/')
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
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
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
            url = add_host(href, 'https://python.libhunt.com/')
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
            article['title'] = title
            article['desc'] = desc
            article['url'] = url
            article['url_key'] = get_url_key(article['url'])
            articles.append(article)
        except Exception:
            logger.error(f'{source} crawl failed: {traceback.format_exc()}')
            break
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
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
            url = add_host(href, 'https://realpython.com/')
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
            article['title'] = title
            article['desc'] = ''
            article['url'] = url
            article['url_key'] = get_url_key(article['url'])
            articles.append(article)
        except Exception:
            logger.error(f'{source} crawl failed: {traceback.format_exc()}')
            break
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
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
            if 'Python Software Foundation: ' in title:
                # 已经单独收录过, 不需要再收录一次
                continue
            if description:
                desc = fromstring(description[0]).text_content()
                # 去掉 <>
                desc = re.sub('<[^>]*>', ' ', desc)
                # 只保留第一个换行前面的
                desc = shorten_desc(desc)
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
            article['title'] = title
            article['desc'] = desc
            article['url'] = url
            article['url_key'] = get_url_key(article['url'])
            articles.append(article)
        except Exception:
            logger.error(f'{source} crawl failed: {traceback.format_exc()}')
            break
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
    return articles


@register_online
async def julien_danjou() -> list:
    """Julien Danjou"""
    # 历史文章只要不断改页码迭代就好了
    source = 'Julien Danjou'
    articles: list = []
    seed = 'https://julien.danjou.info/page/1/'
    r = await req.get(seed, retry=1, timeout=20, headers={"User-Agent": UA})
    if not r:
        logger.error(f'{source} crawl failed: {r}, {r.text}')
        return articles
    scode = r.text
    items = fromstring(scode).cssselect('.post-feed>article.post-card')
    # 判断发布时间如果是 1 小时前就 break
    break_time = ttime(time.time() - 60 * 60)
    host = 'https://julien.danjou.info/'
    for item in items:
        try:
            article = {
                'source': source,
                'level': content_sources_dict[source]['level']
            }
            href = item.cssselect('a.post-card-content-link')[0].get('href', '')
            if not href:
                raise ValueError(f'{source} not found href from {seed}')
            url = add_host(href, host)
            title = (item.cssselect('h2.post-card-title') or
                     [null_tree])[0].text
            desc = (item.cssselect('.post-card-excerpt>p') or
                    [null_tree])[0].text
            if not (title and url):
                raise ValueError(f'{source} no title {url}')
            detail_resp = await req.get(
                url,
                verify=0,
                headers={
                    "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36'
                })
            if not detail_resp:
                raise ValueError(f'{source} request href failed {detail_resp}')
            detail_scode = detail_resp.text
            raw_pub_time = find_one(
                'property="article:published_time" content="(.+?)"',
                detail_scode)[1]
            # 2019-05-06T08:58:00.000Z
            ts_publish = ttime(ptime(raw_pub_time,
                                     fmt='%Y-%m-%dT%H:%M:%S.000Z'))
            cover_item = item.cssselect('img.post-card-image')
            if cover_item:
                cover = cover_item[0].get('src', '')
                if cover:
                    article['cover'] = add_host(cover, host)
            article['ts_publish'] = ts_publish
            article['title'] = title
            article['desc'] = desc
            article['url'] = url
            article['url_key'] = get_url_key(article['url'])
            articles.append(article)
            if ts_publish < break_time:
                # 文章的发布时间超过抓取间隔, 则 break
                break
        except Exception:
            logger.error(f'{source} crawl failed: {traceback.format_exc()}')
            break
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
    return articles


@register_online
async def doughellmann() -> list:
    """Doug Hellmann"""
    source = 'Doug Hellmann'
    articles: list = []
    max_page = 1
    seed = 'https://doughellmann.com/blog/page/{page}/'
    for page in range(1, max_page + 1):
        r = await req.get(seed.format(page=page),
                          retry=1,
                          timeout=20,
                          headers={"User-Agent": UA})
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        scode = r.text
        items = fromstring(scode).cssselect('#main>article')
        if max_page > 1:
            logger.info(f'{source} crawling page {page}, + {len(items)} items')
            if not items and page > 1:
                logger.info(f'{source} break for page {page} has no items')
                break
        for item in items:
            try:
                article = {
                    'source': source,
                    'level': content_sources_dict[source]['level']
                }
                title = item.cssselect('.entry-title>a')[0].text
                url = item.cssselect('.entry-title>a')[0].get('href')
                desc = item.cssselect('.entry-content')[0].text_content()
                pub_time = item.cssselect('time.entry-date')[0].get('datetime')
                ts_publish = ttime(ptime(pub_time, fmt='%Y-%m-%dT%H:%M:%S%z'))
                article['ts_publish'] = ts_publish
                article['title'] = title
                article['desc'] = shorten_desc(desc)
                article['url'] = url
                article['url_key'] = get_url_key(article['url'])
                articles.append(article)
            except Exception:
                logger.error(f'{source} crawl failed: {traceback.format_exc()}')
                break
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
    return articles


@register_online
# @register_history
# @register_test
async def mouse_vs_python() -> list:
    """The Mouse Vs. The Python"""
    source = 'The Mouse Vs. The Python'
    articles: list = []
    max_page = 1
    # max_page = 101
    seed = 'https://www.blog.pythonlibrary.org/page/{page}/'
    for page in range(1, max_page + 1):
        r = await req.get(seed.format(page=page),
                          retry=1,
                          timeout=20,
                          headers={"User-Agent": UA})
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        scode = r.text
        items = fromstring(scode).cssselect('#content>article')
        if max_page > 1:
            logger.info(f'{source} crawling page {page}, + {len(items)} items')
        if not items:
            if page > 1:
                logger.info(f'{source} break for page {page} has no items')
            break
        for item in items:
            try:
                article = {
                    'source': source,
                    'level': content_sources_dict[source]['level']
                }
                title = item.cssselect('.entry-title>a')[0].text
                url = item.cssselect('.entry-title>a')[0].get('href')
                desc = item.cssselect('.entry-content')[0].text_content()
                pub_time = item.cssselect('time.entry-date')[0].get('datetime')
                ts_publish = ttime(ptime(pub_time, fmt='%Y-%m-%dT%H:%M:%S%z'))
                article['ts_publish'] = ts_publish
                article['title'] = title
                article['desc'] = shorten_desc(desc)
                article['url'] = url
                article['url_key'] = get_url_key(article['url'])
                articles.append(article)
            except Exception:
                logger.error(f'{source} crawl failed: {traceback.format_exc()}')
                break
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
    return articles


@register_online
# @register_history
# @register_test
async def infoq_python() -> list:
    """InfoQ"""
    source = 'InfoQ'
    articles: list = []
    max_page = 1
    # max_page = 101
    curl_string = r'''curl 'https://www.infoq.cn/public/v1/article/getList' -H 'Origin: https://www.infoq.cn' -H 'Accept-Encoding: gzip, deflate, br' -H 'Accept-Language: zh-CN,zh;q=0.9' -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36' -H 'Content-Type: application/json' -H 'Accept: application/json, text/plain, */*' -H 'Referer: https://www.infoq.cn/topic/python' -H 'Cookie: SERVERID=0|0|0' -H 'Connection: keep-alive' -H 'DNT: 1' --data-binary '{"type":1,"size":12,"id":50,"score":0}' --compressed'''
    request_args = curlparse(curl_string)
    for page in range(1, max_page + 1):
        r = await req.request(retry=1, timeout=20, **request_args)
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        items = r.json().get('data') or []
        if max_page > 1:
            logger.info(f'{source} crawling page {page}, + {len(items)} items')
            if items:
                # 调整上一页最后一个 score 实现翻页
                data = json.loads(request_args['data'])
                data['score'] = items[-1]['score']
                request_args['data'] = json.dumps(data).encode('u8')
            elif page > 1:
                logger.info(f'{source} break for page {page} has no items')
                break
        for item in items:
            try:
                article = {
                    'source': source,
                    'level': content_sources_dict[source]['level']
                }
                title = item['article_title']
                url = f"https://www.infoq.cn/article/{item['uuid']}"
                desc = item['article_summary']
                ts_publish = ttime(item['publish_time'])
                article['ts_publish'] = ts_publish
                article['title'] = title
                article['desc'] = shorten_desc(desc)
                article['url'] = url
                article['url_key'] = get_url_key(article['url'])
                articles.append(article)
            except Exception:
                logger.error(f'{source} crawl failed: {traceback.format_exc()}')
                break
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
    return articles


@register_online
# @register_history
# @register_test
async def hn_python() -> list:
    """Hacker News"""
    source = 'Hacker News'
    articles: list = []
    max_page = 999
    # 默认收录 24 小时内的 5 points 以上
    min_points = 5
    now_ts = int(time.time())
    ts_start = now_ts - 86400
    ts_end = now_ts
    # 历史文章收录 90 天内的历史文章, 对方有个每次 query 1000 的上限配置 paginationLimitedTo
    # 如果需要更久的, 不断修改起止时间就可以了
    # ts_start = now_ts - 86400 * 90
    # ts_end = now_ts
    per_page = 100
    api = 'https://hn.algolia.com/api/v1/search_by_date'
    # tags=story&query=python&numericFilters=created_at_i%3E1553174400,points%3E1&page=2&hitsPerPage=10
    params = {
        'tags': 'story',
        'query': 'python',
        'numericFilters': f'created_at_i>={ts_start},created_at_i<={ts_end},points>={min_points}',
        'page': 0,
        'hitsPerPage': per_page,
    }
    for page in range(max_page):
        params['page'] = page
        r = await req.get(api,
                          params=params,
                          retry=1,
                          timeout=20,
                          headers={"User-Agent": UA})
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        items = r.json().get('hits') or []
        if not items:
            break
        if page > 0:
            logger.info(f'{source} crawling page {page}, + {len(items)} items')
            if not items and page > 0:
                logger.info(f'{source} break for page {page} has no items')
                break
        for item in items:
            try:
                article = {
                    'source': source,
                    'level': content_sources_dict[source]['level']
                }
                title = item['title']
                url = item['url'] or ''
                if not url:
                    url = f'https://news.ycombinator.com/item?id={item["objectID"]}'
                desc = item['story_text'] or ''
                ts_publish = ttime(item['created_at_i'])
                article['ts_publish'] = ts_publish
                article['title'] = title
                article['desc'] = shorten_desc(desc)
                article['url'] = url
                article['url_key'] = get_url_key(article['url'])
                articles.append(article)
            except Exception:
                logger.error(f'{source} crawl failed: {traceback.format_exc()}')
                break
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
    return articles


@register_online
# @register_history
# @register_test
async def snarky() -> list:
    """Brett Cannon"""
    source = 'Brett Cannon'
    articles: list = []
    max_page = 1
    api = 'https://snarky.ca/page/{page}/'
    # 判断发布时间如果是 1 小时前就 break
    break_time = ttime(time.time() - 60 * 60)
    host = 'https://snarky.ca/'
    for page in range(1, max_page + 1):
        seed = api.format(page=page)
        r = await req.get(seed, retry=1, timeout=20, headers={"User-Agent": UA})
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        scode = r.text
        items = fromstring(scode).cssselect('.post-feed>article.post-card')
        if not items:
            break
        for item in items:
            try:
                article = {
                    'source': source,
                    'level': content_sources_dict[source]['level']
                }
                href = item.cssselect('a.post-card-content-link')[0].get(
                    'href', '')
                if not href:
                    raise ValueError(f'{source} not found href from {seed}')
                url = add_host(href, host)
                title = (item.cssselect('h2.post-card-title') or
                         [null_tree])[0].text
                desc = (item.cssselect('.post-card-excerpt>p') or
                        [null_tree])[0].text
                if not (title and url):
                    raise ValueError(f'{source} no title {url}')
                detail_resp = await req.get(
                    url,
                    verify=0,
                    headers={
                        "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36'
                    })
                if not detail_resp:
                    raise ValueError(
                        f'{source} request href failed {detail_resp}')
                detail_scode = detail_resp.text
                raw_pub_time = find_one(
                    'property="article:published_time" content="(.+?)"',
                    detail_scode)[1]
                # 2019-05-06T08:58:00.000Z
                ts_publish = ttime(
                    ptime(raw_pub_time, fmt='%Y-%m-%dT%H:%M:%S.000Z'))
                cover_item = item.cssselect('img.post-card-image')
                if cover_item:
                    cover = cover_item[0].get('src', '')
                    if cover:
                        article['cover'] = add_host(cover, host)
                article['ts_publish'] = ts_publish
                article['title'] = title
                article['desc'] = desc
                article['url'] = url
                article['url_key'] = get_url_key(article['url'])
                articles.append(article)
                if ts_publish < break_time:
                    # 文章的发布时间超过抓取间隔, 则 break
                    break
            except Exception:
                logger.error(f'{source} crawl failed: {traceback.format_exc()}')
                break
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
    return articles


@register_online
# @register_history
# @register_test
async def jiqizhixin() -> list:
    """机器之心"""
    source = '机器之心'
    articles: list = []
    max_page = 1
    # 有 cookie 和 防跨域验证
    curl_string = r'''curl 'https://www.jiqizhixin.com/api/v1/search?type=articles&page=1&keywords=python&published=0&is_exact_match=false&search_internet=true&sort=time' -H 'Cookie: ahoy_visitor=1; _Synced_session=2' -H 'DNT: 1' -H 'Accept-Encoding: gzip, deflate, br' -H 'Accept-Language: zh-CN,zh;q=0.9' -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36' -H 'Accept: */*' -H 'Referer: https://www.jiqizhixin.com/search/article?keywords=python&search_internet=true&sort=time' -H 'X-Requested-With: XMLHttpRequest' -H 'If-None-Match: W/"3e034aa5e8cb79dd92652f5ba70a65a5"' -H 'Connection: keep-alive' --compressed'''
    request_args = curlparse(curl_string)
    for page in range(1, max_page + 1):
        # 部分时候请求返回结果为空, 需要重试
        for _ in range(3):
            r = await req.request(retry=1, timeout=20, **request_args)
            if not r:
                logger.error(f'{source} crawl failed: {r}, {r.text}')
                return articles
            try:
                items = r.json().get('articles', {}).get('nodes', [])
                break
            except json.decoder.JSONDecodeError:
                await asyncio.sleep(2)
                continue
        else:
            # 试了 3 次都没 break, 放弃
            return articles
        if max_page > 1:
            logger.info(f'{source} crawling page {page}, + {len(items)} items')
            # 翻页, 修改 page
            curl_string = re.sub(r'&page=\d+', f'&page={page + 1}', curl_string)
            request_args = curlparse(curl_string)
        if not r.json().get('articles', {}).get('hasNextPage'):
            break
        for item in items:
            try:
                article = {
                    'source': source,
                    'level': content_sources_dict[source]['level']
                }
                desc = item['content']
                # 2019/05/27 00:09
                article['ts_publish'] = ttime(
                    ptime(item['published_at'], fmt='%Y/%m/%d %H:%M'))
                title = item.get('title') or ''
                title = title.replace('<em>Python</em>',
                                      'Python').replace('<em>python</em>',
                                                        'Python')
                article['title'] = title
                article['cover'] = item.get('cover_image_url') or ''
                article['desc'] = f'「{item["author"]}」 {shorten_desc(desc)}'
                article['url'] = item['path']
                article['url_key'] = get_url_key(article['url'])
                articles.append(article)
            except Exception:
                logger.error(f'{source} crawl failed: {traceback.format_exc()}')
                break
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
    return articles
