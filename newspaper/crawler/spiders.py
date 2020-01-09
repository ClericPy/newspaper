import asyncio
import json
import traceback
import typing
import zlib

from lxml.html import fromstring, tostring
from lxml.etree import ElementBase
from torequests.dummy import Requests
from torequests.utils import (UA, curlparse, find_one, md5, parse_qsl, ptime,
                              re, time, ttime, unparse_qsl, urlparse,
                              urlunparse, escape)

from ..config import global_configs
from ..loggers import spider_logger as logger

test_spiders = []
online_spiders = []
history_spiders = []
# CHROME_PC_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36'
CHROME_PC_UA = UA.Chrome
friendly_crawling_interval = 1
# default_host_frequency 是默认的单域名并发控制: 每 3 秒一次请求
req = Requests(default_host_frequency=(1, 3))
# 多次请求时的友好抓取频率
# req.set_frequency('zhuanlan.zhihu.com', 1, 3)
req.set_frequency('www.tuicool.com', 1, 3)
# 免费代理
proxy = 'http://218.60.8.99:3129'


class null_tree:
    text = ''

    @classmethod
    def text_content(cls):
        return ''

    def get(self, key, default=''):
        return default

    @classmethod
    def css(cls, item, csspath, idx=0):
        return (item.cssselect(csspath) or [cls])[idx]

    @classmethod
    def tostring(cls, doc, **kwargs):
        if isinstance(doc, ElementBase):
            return tostring(doc, **kwargs)
        else:
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


def add_host(url: str, host: str) -> str:
    if not url:
        return ''
    if re.match('^https?://', url):
        return url
    if url.startswith('//'):
        return f'https:{url}'
    if not host.endswith('/'):
        host = f'{host}/'
    return re.sub('^/', host, url)


def shorten_desc(desc: str) -> str:
    """Shorten the desc too long (more than 50)."""
    if not desc:
        return ''
    # remain sentence before ./\n/。/!
    desc = re.sub(r'(.{50,})(\n|\.|。|！|!|？|\?)\s?[\s\S]+', r'\1\2', desc)
    # remove html tag
    desc = re.sub('<[^>]+>', '', desc).strip()
    return escape(desc)


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


async def common_spider_zhihu_zhuanlan(name, source, limit=10):
    articles = []
    offset: int = 0
    # 分页
    chunk_size: int = 50
    # 最多只要 2000 篇，再多没意义
    for _ in range(2000 // chunk_size):
        _limit = min((limit - offset, chunk_size))
        # or limit == offset
        if not _limit:
            break
        api: str = f'https://zhuanlan.zhihu.com/api/columns/{name}/articles?limit={_limit}&offset={offset}'
        r = await req.get(
            api,
            ssl=False,
            headers={
                "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36'
            })
        if not r:
            logger.info(
                f'crawl zhihu_zhuanlan {name} limit={limit} failed: {r}')
            return articles
        items = r.json()['data']
        if not items:
            break
        for item in items:
            if not (item['type'] == 'article' and item['state'] == 'published'):
                continue
            article: dict = {'source': source}
            article['ts_publish'] = ttime(item['created'])
            article['cover'] = item['image_url']
            article['title'] = item['title']
            article['desc'] = re.sub('<[^>]+>', ' ', item.get('excerpt') or '')
            article['url'] = item['url']
            article['url_key'] = get_url_key(article['url'])
            articles.append(article)
        offset += _limit

    return articles


async def common_spider_tuicool(lang, source, max_page=1, ignore_descs=None):
    articles = []
    langs = {'cn': 1, 'en': 2}
    lang_num = langs[lang]
    host = 'https://www.tuicool.com/'
    this_year = ttime()[:4]
    ignore_descs = ignore_descs or set()
    # 非登录用户只能采集前两页, 想采集更多需要 `_tuicool_session` cookie.
    headers = {
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'If-None-Match': 'W/"41a6894d66c0f07fcfac6ec1d84446a3"',
        'Dnt': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.90 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
        'Referer': 'https://www.tuicool.com/',
        'Host': 'www.tuicool.com',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cookie': '_tuicool_session=',
    }
    proxy = None
    for page in range(0, max_page):
        # st 参数: 0 是按时间顺序, 1 是热门文章
        api: str = f'https://www.tuicool.com/topics/11130000?st=1&lang={lang_num}&pn={page}'
        r = await req.get(api,
                          ssl=False,
                          proxy=proxy,
                          retry=1,
                          timeout=5,
                          headers=headers)
        if not r:
            logger.info(f'crawl tuicool {lang} page={page} failed: {r}')
            return articles
        items = fromstring(
            r.text).cssselect('#list_article>div.list_article_item')
        if max_page > 1:
            logger.info(
                f'{source} crawling page {page}, + {len(items)} items = {len(articles)} articles'
            )
        if not items:
            break
        for item in items:
            article: dict = {'source': source}
            url = null_tree.css(item,
                                '.aricle_item_info>.title>a').get('href', '')
            url = add_host(url, host)
            title = null_tree.css(item, '.aricle_item_info>.title>a').text
            cover = null_tree.css(item,
                                  '.article_thumb_image>img').get('src', '')
            cover = cover.replace(
                'https://static0.tuicool.com/images/abs_img_no_small.jpg', '')
            time_span = null_tree.css(item,
                                      '.aricle_item_info>.tip').text_content()
            raw_time = find_one(r'\d\d-\d\d \d\d:\d\d', time_span)[0]
            if raw_time:
                # 避免是个怪异的时间, ensure 一下
                article['ts_publish'] = ttime(
                    ptime(f'{this_year}-{raw_time}:00'))
            desc = null_tree.css(
                item,
                '.aricle_item_info>div.tip>span:nth-of-type(1)').text.strip()
            if desc in ignore_descs:
                continue
            article['cover'] = cover
            article['title'] = title
            article['desc'] = desc
            article['url'] = url
            article['url_key'] = get_url_key(article['url'])
            articles.append(article)
    return articles


@register_online
async def python_news() -> list:
    """Python Software Foundation News"""
    source: str = 'Python Software Foundation News'
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
                article: dict = {'source': source}
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
    source: str = 'Python Software Foundation News'
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
                article: dict = {'source': source}
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
    source: str = 'Python Weekly'
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
            article: dict = {'source': source}
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
                ssl=False,
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
    source: str = 'Python Weekly'
    articles: list = []
    for issue_id in range(324, 1000):
        try:
            article: dict = {'source': source}
            article['ts_publish'] = _python_weekly_calculate_date(issue_id)
            detail_url = f'https://mailchi.mp/pythonweekly/python-weekly-issue-{issue_id}'
            r = await req.get(
                detail_url,
                ssl=False,
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
    """PyCoder's Weekly"""
    # 把 limit 改 999 就可以抓历史了
    source: str = "PyCoder's Weekly"
    articles: list = []
    # 一周一更, 所以只取第一个就可以了
    limit = 1
    seed = 'https://pycoders.com/issues'
    base_url = find_one('^https?://[^/]+', seed)[0]
    r = await req.get(seed, headers={'User-Agent': CHROME_PC_UA})
    if not r:
        logger.error(f'{source} crawl failed: {r}, {r.text}')
        return articles
    items = re.findall(r'<a href="/issues/\d+">Issue #\d+ .*?</a>', r.text)
    for item in items[:limit]:
        try:
            article: dict = {'source': source}
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
# @register_test
async def importpython() -> list:
    """Import Python"""
    source: str = 'Import Python'
    articles: list = []
    # 一周一更, 所以只取第一个就可以了
    limit = 1
    seed = 'https://importpython.com/newsletter/archive/'
    r = await req.get(seed,
                      retry=1,
                      timeout=20,
                      ssl=False,
                      headers={"User-Agent": CHROME_PC_UA})
    if not r:
        logger.error(f'{source} crawl failed: {r}, {r.text}')
        return articles
    items = fromstring(r.text).cssselect('#tourpackages-carousel>.row>div')
    for item in items[:limit]:
        try:
            article: dict = {'source': source}
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
    source: str = 'Awesome Python Newsletter'
    articles: list = []
    # 一周一更, 所以只取第一个就可以了
    limit = 1
    seed = 'https://python.libhunt.com/newsletter/archive'
    r = await req.get(seed,
                      retry=1,
                      timeout=20,
                      headers={"User-Agent": CHROME_PC_UA})
    if not r:
        logger.error(f'{source} crawl failed: {r}, {r.text}')
        return articles
    hrefs = re.findall(
        r'<td class="text-right">\s*<a href=\'(/newsletter/\d+)\'>', r.text)
    for href in hrefs[:limit]:
        try:
            article: dict = {'source': source}
            url = add_host(href, 'https://python.libhunt.com/')
            r = await req.get(url,
                              retry=2,
                              timeout=15,
                              headers={"User-Agent": CHROME_PC_UA})
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
    source: str = 'Real Python'
    articles: list = []
    limit = 20
    seed = 'https://realpython.com/'
    r = await req.get(seed,
                      retry=1,
                      timeout=20,
                      headers={"User-Agent": CHROME_PC_UA})
    if not r:
        logger.error(f'{source} crawl failed: {r}, {r.text}')
        return articles
    items = fromstring(r.text).cssselect('div[class="card border-0"]')
    for item in items[:limit]:
        try:
            article: dict = {'source': source}
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
    source: str = 'Planet Python'
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
            article: dict = {'source': source}
            guid = item.xpath('./guid/text()')
            title = item.xpath('./title/text()')
            description = item.xpath('./description/text()')
            pubDate = item.xpath('./pubdate/text()')
            if not (guid and title):
                continue
            url = guid[0]
            title = title[0]
            if 'بايثون العربي' in title:
                continue
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
    source: str = 'Julien Danjou'
    articles: list = []
    seed = 'https://julien.danjou.info/page/1/'
    r = await req.get(seed,
                      retry=1,
                      timeout=20,
                      headers={"User-Agent": CHROME_PC_UA})
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
            article: dict = {'source': source}
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
                ssl=False,
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
    source: str = 'Doug Hellmann'
    articles: list = []
    max_page: int = 1
    seed = 'https://doughellmann.com/blog/page/{page}/'
    for page in range(1, max_page + 1):
        r = await req.get(seed.format(page=page),
                          retry=1,
                          timeout=20,
                          headers={"User-Agent": CHROME_PC_UA})
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        scode = r.text
        items = fromstring(scode).cssselect('#main>article')
        if max_page > 1:
            logger.info(
                f'{source} crawling page {page}, + {len(items)} items = {len(articles)} articles'
            )
            if not items and page > 1:
                logger.info(f'{source} break for page {page} has no items')
                break
        for item in items:
            try:
                article: dict = {'source': source}
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
    source: str = 'The Mouse Vs. The Python'
    articles: list = []
    max_page: int = 1
    # max_page:int = 101
    seed = 'https://www.blog.pythonlibrary.org/page/{page}/'
    for page in range(1, max_page + 1):
        r = await req.get(seed.format(page=page),
                          retry=1,
                          timeout=20,
                          headers={"User-Agent": CHROME_PC_UA})
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        scode = r.text
        items = fromstring(scode).cssselect('#content>article')
        if max_page > 1:
            logger.info(
                f'{source} crawling page {page}, + {len(items)} items = {len(articles)} articles'
            )
        if not items:
            if page > 1:
                logger.info(f'{source} break for page {page} has no items')
            break
        for item in items:
            try:
                article: dict = {'source': source}
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
    source: str = 'InfoQ'
    articles: list = []
    max_page: int = 1
    # max_page:int = 101
    curl_string = r'''curl 'https://www.infoq.cn/public/v1/article/getList' -H 'Origin: https://www.infoq.cn' -H 'Accept-Encoding: gzip, deflate, br' -H 'Accept-Language: zh-CN,zh;q=0.9' -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36' -H 'Content-Type: application/json' -H 'Accept: application/json, text/plain, */*' -H 'Referer: https://www.infoq.cn/topic/python' -H 'Cookie: SERVERID=0|0|0' -H 'Connection: keep-alive' -H 'DNT: 1' --data-binary '{"type":1,"size":12,"id":50,"score":0}' --compressed'''
    request_args = curlparse(curl_string)
    for page in range(1, max_page + 1):
        r = await req.request(retry=1, timeout=20, **request_args)
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        items = r.json().get('data') or []
        if max_page > 1:
            logger.info(
                f'{source} crawling page {page}, + {len(items)} items = {len(articles)} articles'
            )
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
                article: dict = {'source': source}
                desc = shorten_desc(item['article_summary'])
                if '本文分享 方巍' in desc:
                    continue
                title = item['article_title']
                url = f"https://www.infoq.cn/article/{item['uuid']}"
                ts_publish = ttime(item['publish_time'])
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
# @register_history
# @register_test
async def hn_python() -> list:
    """Hacker News"""
    source: str = 'Hacker News'
    articles: list = []
    max_page = 999
    # 默认收录 24 小时内的 3 points 以上
    min_points = 3
    now_ts = int(time.time())
    ts_start = now_ts - 86400
    ts_end = now_ts
    # 历史文章收录 90 天内的历史文章, 对方有个每次 query 1000 的上限配置 paginationLimitedTo
    # 如果需要更久的, 不断修改起止时间就可以了
    # ts_start = now_ts - 86400 * 90
    # ts_end = now_ts
    per_page: int = 100
    api: str = 'https://hn.algolia.com/api/v1/search_by_date'
    # tags=story&query=python&numericFilters=created_at_i%3E1553174400,points%3E1&page=2&hitsPerPage=10
    params: dict = {
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
                          headers={"User-Agent": CHROME_PC_UA})
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        items = r.json().get('hits') or []
        if not items:
            break
        if page > 0:
            logger.info(
                f'{source} crawling page {page}, + {len(items)} items = {len(articles)} articles'
            )
            if not items and page > 0:
                logger.info(f'{source} break for page {page} has no items')
                break
        for item in items:
            try:
                article: dict = {'source': source}
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
    source: str = 'Brett Cannon'
    articles: list = []
    max_page: int = 1
    api: str = 'https://snarky.ca/page/{page}/'
    # 判断发布时间如果是 1 小时前就 break
    break_time = ttime(time.time() - 60 * 60)
    host = 'https://snarky.ca/'
    for page in range(1, max_page + 1):
        seed = api.format(page=page)
        r = await req.get(seed,
                          retry=1,
                          timeout=20,
                          headers={"User-Agent": CHROME_PC_UA})
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        scode = r.text
        items = fromstring(scode).cssselect('.post-feed>article.post-card')
        if not items:
            break
        for item in items:
            try:
                article: dict = {'source': source}
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
                    ssl=False,
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
    source: str = '机器之心'
    articles: list = []
    max_page: int = 1
    # 有 cookie 和 防跨域验证
    curl_string = r'''curl 'https://www.jiqizhixin.com/api/v1/search?type=articles&page=1&keywords=python&published=0&is_exact_match=false&search_internet=true&sort=time' -H 'Cookie: ahoy_visitor=1; _Synced_session=2' -H 'DNT: 1' -H 'Accept-Encoding: gzip, deflate, br' -H 'Accept-Language: zh-CN,zh;q=0.9' -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36' -H 'Accept: */*' -H 'Referer: https://www.jiqizhixin.com/search/article?keywords=python&search_internet=true&sort=time' -H 'X-Requested-With: XMLHttpRequest' -H 'If-None-Match: W/"3e034aa5e8cb79dd92652f5ba70a65a5"' -H 'Connection: keep-alive' --compressed'''
    request_args = curlparse(curl_string)
    for page in range(1, max_page + 1):
        # 部分时候请求返回结果为空, 需要重试
        for _ in range(2, 5):
            r = await req.request(retry=1, timeout=20, **request_args)
            if not r:
                logger.error(f'{source} crawl failed: {r}, {r.text}')
                return articles
            try:
                items = r.json().get('articles', {}).get('nodes', [])
                if not items:
                    continue
                break
            except json.decoder.JSONDecodeError:
                await asyncio.sleep(_)
                continue
        else:
            # 试了 3 次都没 break, 放弃
            return articles
        if max_page > 1:
            logger.info(
                f'{source} crawling page {page}, + {len(items)} items = {len(articles)} articles'
            )
            # 翻页, 修改 page
            curl_string = re.sub(r'&page=\d+', f'&page={page + 1}', curl_string)
            request_args = curlparse(curl_string)
        if not r.json().get('articles', {}).get('hasNextPage'):
            break
        for item in items:
            try:
                article: dict = {'source': source}
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


@register_online
# @register_history
# @register_test
async def lilydjwg() -> list:
    """依云's Blog"""
    source: str = "依云's Blog"
    articles: list = []
    max_page: int = 1
    seed = 'https://blog.lilydjwg.me/tag/python?page={page}'
    for page in range(1, max_page + 1):
        r = await req.get(seed.format(page=page),
                          retry=1,
                          timeout=20,
                          headers={"User-Agent": CHROME_PC_UA})
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        scode = r.content.decode('u8')
        items = fromstring(scode).cssselect('#content>.posttotal')
        if not items:
            break
        host = 'https://blog.lilydjwg.me/'
        if max_page > 1:
            logger.info(
                f'{source} crawling page {page}, + {len(items)} items = {len(articles)} articles'
            )
        for item in items:
            try:
                article: dict = {'source': source}
                title = item.cssselect('.storytitle>a')[0].text
                href = item.cssselect('.storytitle>a')[0].get('href', '')
                url = add_host(href, host).replace(
                    'https://lilydjwg.is-programmer.com/', host)
                desc = shorten_desc((item.cssselect('.post_brief>p') or
                                     [null_tree])[0].text_content())
                cover = (item.cssselect('img') or [null_tree])[0].get('src', '')
                month, day, year = item.cssselect(
                    '.date')[0].text_content().strip().split()
                month = f'0{month}' [-2:]
                day = f'0{day}' [-2:]
                article['ts_publish'] = ttime(
                    ptime(f'{year}/{month}/{day}', fmt='%Y/%m/%d'))
                article['title'] = title
                article['cover'] = cover
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
# @register_history
# @register_test
async def dev_io() -> list:
    """DEV Community"""
    source: str = "DEV Community"
    articles: list = []
    max_page: int = 1
    per_page: int = 15
    filt_score: int = 10
    curl_string1 = r'''curl 'https://ye5y9r600c-3.algolianet.com/1/indexes/ordered_articles_production/query?x-algolia-agent=Algolia%20for%20vanilla%20JavaScript%203.20.3&x-algolia-application-id=YE5Y9R600C&x-algolia-api-key=YWVlZGM3YWI4NDg3Mjk1MzJmMjcwNDVjMjIwN2ZmZTQ4YTkxOGE0YTkwMzhiZTQzNmM0ZGFmYTE3ZTI1ZDFhNXJlc3RyaWN0SW5kaWNlcz1zZWFyY2hhYmxlc19wcm9kdWN0aW9uJTJDVGFnX3Byb2R1Y3Rpb24lMkNvcmRlcmVkX2FydGljbGVzX3Byb2R1Y3Rpb24lMkNDbGFzc2lmaWVkTGlzdGluZ19wcm9kdWN0aW9uJTJDb3JkZXJlZF9hcnRpY2xlc19ieV9wdWJsaXNoZWRfYXRfcHJvZHVjdGlvbiUyQ29yZGVyZWRfYXJ0aWNsZXNfYnlfcG9zaXRpdmVfcmVhY3Rpb25zX2NvdW50X3Byb2R1Y3Rpb24lMkNvcmRlcmVkX2NvbW1lbnRzX3Byb2R1Y3Rpb24%3D' -H 'accept: application/json' -H 'Referer: https://dev.to/' -H 'Origin: https://dev.to' -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36' -H 'DNT: 1' --data '{"params":"query=*&hitsPerPage=''' + str(
        per_page)
    curl_string3 = r'''&attributesToHighlight=%5B%5D&tagFilters=%5B%22python%22%5D"}' --compressed'''
    for page in range(0, max_page):
        curl_string2 = f'&page={page}'
        curl_string = f'{curl_string1}{curl_string2}{curl_string3}'
        request_args = curlparse(curl_string)
        r = await req.request(retry=1, timeout=20, **request_args)
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        items = r.json().get('hits') or []
        if not items:
            break
        host = 'https://dev.to/'
        if max_page > 1:
            logger.info(
                f'{source} crawling page {page}, + {len(items)} items = {len(articles)} articles'
            )
        for item in items:
            try:
                if item['score'] < filt_score:
                    # filt by min score
                    continue
                article: dict = {'source': source}
                title = item['title']
                path = item['path']
                url = add_host(path, host)
                desc = item['user']['name']
                article['ts_publish'] = ttime(item['published_at_int'])
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
# @register_history
# @register_test
async def zhihu_zhuanlan_pythoncat() -> list:
    """Python猫"""
    source: str = "Python猫"
    name: str = 'pythonCat'
    articles: list = []
    limit = 10
    articles = await common_spider_zhihu_zhuanlan(name, source, limit=limit)
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
    return articles


@register_online
# @register_history
# @register_test
async def zhihu_zhuanlan_python_cn() -> list:
    """Python之美"""
    source: str = "Python之美"
    name: str = 'python-cn'
    articles: list = []
    limit = 10
    articles = await common_spider_zhihu_zhuanlan(name, source, limit=limit)
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
    return articles


@register_online
# @register_history
# @register_test
async def zhihu_zhuanlan_pythoncxy() -> list:
    """Python程序员"""
    source: str = "Python程序员"
    name: str = 'pythoncxy'
    articles: list = []
    limit = 10
    articles = await common_spider_zhihu_zhuanlan(name, source, limit=limit)
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
    return articles


@register_online
# @register_history
# @register_test
async def zhihu_zhuanlan_c_111369541() -> list:
    """Python头条"""
    source: str = "Python头条"
    name: str = 'c_111369541'
    articles: list = []
    limit = 10
    articles = await common_spider_zhihu_zhuanlan(name, source, limit=limit)
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
    return articles


@register_online
# @register_history
# @register_test
async def cuiqingcai() -> list:
    """静觅"""
    source: str = "静觅"
    articles: list = []
    max_page: int = 1
    # max_page = 20
    api: str = 'https://cuiqingcai.com/category/technique/python/page/'
    now = ttime()
    this_date = now[5:10]
    this_year = now[:4]
    last_year_int = int(this_year) - 1
    timestamp_today_0 = ptime(now[:10] + ' 00:00:00')

    def translate_time_text(raw_time):
        if not raw_time:
            return ''
        raw_time = raw_time.strip()
        # 针对每种情况做时间转换
        # 4个月前 (02-21)
        # 2天前
        # 4年前 (2015-02-12)
        # 先尝试取得横线/:分割的时间, 取不到的应该是 n 天前的情况
        date = find_one(r'([\d:\- ]+)', raw_time)[1]
        if date:
            if re.match(r'^\d\d-\d\d$', date):
                # 只有月日
                # 这里有可能遇到的是去年的月份, 所以先判断
                if date >= this_date:
                    date = f'{last_year_int}-{date}'
                else:
                    date = f'{this_year}-{date}'
                result = f'{date} 00:00:00'
            elif re.match(r'^\d\d\d\d-\d\d-\d\d$', date):
                # 有年月日
                result = f'{date} 00:00:00'
            elif re.match(r'^\d\d\d\d-\d\d-\d\d \d\d:\d\d$', date):
                # 有年月日时分
                result = f'{date}:00'
            elif re.match(r'^\d\d\d\d-\d\d-\d\d \d:\d\d$', date):
                # 有年月日时分
                result = f'{date[:11]}0{date[11:]}:00'
            else:
                raise ValueError(f'bad time pattern {raw_time}')
        elif re.match(r'^\d+小时前$', raw_time):
            n_hour = int(find_one(r'\d+', raw_time)[0])
            result = ttime(timestamp_today_0 - n_hour * 3600)
        elif re.match(r'^\d+天前$', raw_time):
            n_day = int(find_one(r'\d+', raw_time)[0])
            result = ttime(timestamp_today_0 - n_day * 86400)
        else:
            raise ValueError(f'bad time pattern {raw_time}')
        return result

    for page in range(1, max_page + 1):
        seed = f'{api}{page}'
        r = await req.get(
            seed,
            retry=1,
            timeout=20,
            ssl=False,
            headers={
                "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36'
            })
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        items = fromstring(
            r.content.decode('u8')).cssselect('div.content>article')
        if not items:
            break
        if max_page > 1:
            logger.info(
                f'{source} crawling page {page}, + {len(items)} items = {len(articles)} articles'
            )
        for item in items:
            try:
                article: dict = {'source': source}
                title = null_tree.css(item, 'header>h2>a').text
                url = null_tree.css(item, 'header>h2>a').get('href', '')
                desc = null_tree.css(item, '.note').text_content()
                cover = null_tree.css(item, 'img.thumb').get('src', '')
                raw_time_text = null_tree.css(
                    item, 'p > span:nth-child(2)').text_content()
                article['ts_publish'] = translate_time_text(raw_time_text)
                article['title'] = title
                article['cover'] = cover
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
# @register_history
# @register_test
async def tuicool_cn() -> list:
    """推酷(中文)"""
    source: str = "推酷(中文)"
    articles: list = []
    max_page: int = 1
    articles = await common_spider_tuicool(
        'cn',
        source,
        max_page=max_page,
        ignore_descs={'稀土掘金', 'Python猫', 'InfoQ'})
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
    return articles


@register_online
# @register_history
# @register_test
async def tuicool_en() -> list:
    """推酷(英文)"""
    source: str = "推酷(英文)"
    articles: list = []
    max_page: int = 1
    articles = await common_spider_tuicool('en',
                                           source,
                                           max_page=max_page,
                                           ignore_descs={'Real Python'})
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
    return articles


@register_online
# @register_history
# @register_test
async def kf_toutiao() -> list:
    """稀土掘金"""
    source: str = "稀土掘金"
    articles: list = []
    max_page: int = 1
    per_page: int = 20
    sort_by = 'rankIndex'  # 'createdAt' 是按时间顺序
    api: str = 'https://timeline-merger-ms.juejin.im/v1/get_tag_entry'
    params: dict = {
        'src': 'web',
        'tagId': '559a7227e4b08a686d25744f',
        'page': 0,
        'pageSize': per_page,
        'sort': sort_by
    }

    ignore_usernames: set = {'豌豆花下猫'}
    for page in range(0, max_page):
        params['page'] = page
        r = await req.get(
            api,
            params=params,
            ssl=False,
            # proxy=proxy,
            retry=1,
            headers={
                'Referer': 'https://juejin.im/tag/Python?sort=popular',
                'Origin': 'https://juejin.im',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.90 Safari/537.36',
                'Dnt': '1'
            },
        )
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        items = r.json().get('d', {}).get('entrylist', [])
        if not items:
            break
        if max_page > 1:
            logger.info(
                f'{source} crawling page {page}, + {len(items)} items = {len(articles)} articles'
            )
        for item in items:
            try:
                article: dict = {'source': source}
                # 过滤一下已收录过的源
                if item.get('user', {}).get('username', '') in ignore_usernames:
                    continue
                # 2019-05-05T03:51:12.886Z
                gmt_time = re.sub(r'\..*', '',
                                  item['createdAt']).replace('T', ' ')
                ts_publish = ttime(ptime(gmt_time, tzone=0))
                article['ts_publish'] = ts_publish
                article['lang'] = 'en' if item['english'] else 'cn'
                article['title'] = item['title']
                article['cover'] = item['screenshot']
                article['desc'] = item['summaryInfo']
                article['url'] = item['originalUrl']
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
async def freelycode() -> list:
    """Python部落"""
    source: str = "Python部落"
    articles: list = []
    max_page: int = 1
    api: str = 'https://python.freelycode.com/contribution/list/0'
    params: dict = {
        'page_no': 1,
    }
    host: str = 'https://python.freelycode.com/'

    def fix_time(raw_time):
        # 2019-03-27 7:02 a.m.
        # 2019-03-22 9:27 a.m.
        # 2019-07-17 9 a.m.
        raw_time = raw_time.replace('中午', '12:01 p.m.')
        if ':' not in raw_time:
            raw_time = f'{raw_time[:-5]}:00{raw_time[-5:]}'
        raw_time = raw_time.replace('.m.', 'm')
        formated_time = ttime(ptime(raw_time, fmt='%Y-%m-%d %I:%M %p'))
        return formated_time

    for page in range(1, max_page + 1):
        params['page_no'] = page
        r = await req.get(
            api,
            ssl=False,
            params=params,
            # proxy=proxy,
            retry=1,
            headers={
                'Referer': api,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.90 Safari/537.36',
            },
        )
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        scode: str = r.content.decode('u8', 'ignore')
        items: list = fromstring(scode).cssselect(
            '.table-bordered tr:nth-child(n+2)')
        if not items:
            break
        if max_page > 1:
            logger.info(
                f'{source} crawling page {page}, + {len(items)} items = {len(articles)} articles'
            )
        for item in items:
            try:
                article: dict = {'source': source}
                title_href = item.cssselect('td:nth-child(2)>a')
                if not title_href:
                    continue
                title: str = title_href[0].text
                href: str = title_href[0].get('href', '')
                url: str = add_host(href, host)
                desc: str = null_tree.css(item, 'td:nth-child(3)').text
                if desc:
                    desc = f'作者: {desc}'
                raw_time: str = null_tree.css(item, 'td:nth-child(4)').text
                ts_publish = fix_time(raw_time)
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
# @register_history
# @register_test
async def miguelgrinberg() -> list:
    """miguelgrinberg"""
    source: str = "miguelgrinberg"
    articles: list = []
    start_page: int = 1
    max_page: int = 1
    api: str = 'https://blog.miguelgrinberg.com/index/page/'
    host: str = 'https://blog.miguelgrinberg.com/'

    for page in range(start_page, max_page + 1):
        page_url = f'{api}{page}'
        r = await req.get(
            page_url,
            ssl=False,
            # proxy=proxy,
            retry=1,
            headers={
                'Referer': page_url,
                'User-Agent': CHROME_PC_UA
            },
        )
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        scode: str = r.content.decode('u8', 'ignore')
        scode = re.sub(r'<!--[\s\S]*?-->', '', scode)
        items: list = fromstring(scode).cssselect('#main>.post')
        if not items:
            break
        if max_page > 1:
            logger.info(
                f'{source} crawling page {page}, + {len(items)} items = {len(articles)} articles'
            )
        for item in items:
            try:
                article: dict = {'source': source}
                title_href = item.cssselect('h1.post-title>a')
                if not title_href:
                    continue
                title: str = title_href[0].text
                href: str = title_href[0].get('href', '')
                url: str = add_host(href, host)
                desc: str = null_tree.css(item, '.post_body>p').text_content()
                raw_time: str = null_tree.css(item, '.date>span').get(
                    'data-timestamp', '').replace('T', ' ').replace('Z', '')
                ts_publish = ttime(ptime(raw_time, tzone=0))
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
async def codingpy() -> list:
    """编程派"""
    source: str = "编程派"
    articles: list = []
    start_page: int = 1
    max_page: int = 1
    api: str = 'https://codingpy.com/article/'
    params: dict = {'page': 1}
    host: str = 'https://codingpy.com/'

    for page in range(start_page, max_page + 1):
        params['page'] = page
        r = await req.get(
            api,
            params=params,
            ssl=False,
            # proxy=proxy,
            retry=1,
            headers={
                'Referer': api,
                'User-Agent': CHROME_PC_UA
            },
        )
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        scode: str = r.content.decode('u8', 'ignore')
        items: list = fromstring(scode).cssselect('.archive-main>article')
        if not items:
            break
        if max_page > 1:
            logger.info(
                f'{source} crawling page {page}, + {len(items)} items = {len(articles)} articles'
            )
        for item in items:
            try:
                article: dict = {'source': source}
                title_href = item.cssselect('.list-item-title>a')
                title: str = title_href[0].text
                href: str = title_href[0].get('href', '')
                bg: str = null_tree.css(item, '.lim-cover').get('style', '')
                # background-image:url(/media/articles/why-python-for-startups.jpg)
                cover: str = find_one(r'background-image:url\((.*?)\)', bg)[1]
                cover = add_host(cover, host)
                url: str = add_host(href, host)
                desc: str = null_tree.css(
                    item, '.list-item-summary>p').text_content()
                raw_time: str = null_tree.css(item,
                                              '.list-item-meta>p>span').text
                # 2015.11.03
                ts_publish = ttime(ptime(raw_time, fmt='%Y.%m.%d'))
                article['ts_publish'] = ts_publish
                article['title'] = title
                article['cover'] = cover
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
async def nedbatchelder() -> list:
    """Ned Batchelder"""
    source: str = "Ned Batchelder"
    articles: list = []
    limit: int = 5
    api: str = 'https://nedbatchelder.com/blog/tag/python.html'
    host: str = 'https://nedbatchelder.com/'
    r = await req.get(
        api,
        ssl=False,
        # proxy=proxy,
        retry=3,
        timeout=5,
        headers={
            'Referer': api,
            'User-Agent': CHROME_PC_UA
        },
    )
    if not r:
        logger.error(f'{source} crawl failed: {r}, {r.text}')
        return articles
    scode: str = r.content.decode('u8', 'ignore')
    container_html = null_tree.tostring(
        null_tree.css(fromstring(scode), '.category')).decode('utf-8')
    if not container_html:
        logger.error(f'{source} not found container_html.')
        return articles
    split_by: str = '<!--split-tag-->'
    container_html = container_html.replace(
        '<p class="date">', f'{split_by}<p class="date">').replace(
            '</div>', '').replace('<div class="category">', '')
    items: list = container_html.split(split_by)[1:limit + 1]
    if not items:
        return articles
    for item in items:
        try:
            article: dict = {'source': source}
            title_href = find_one(r'<p>\s*<a href="([^"]+)">([^<]+?)</a>', item)
            title: str = title_href[2]
            href: str = title_href[1]
            url: str = add_host(href, host)
            raw_time: str = find_one(r'<p class="date">(\d+ .*?\d+):</p>',
                                     item)[1]
            ts_publish = ttime(ptime(raw_time, fmt='%d %b %Y'))
            article['ts_publish'] = ts_publish
            article['title'] = title
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
async def the5fire() -> list:
    """the5fire的技术博客"""
    source: str = "the5fire的技术博客"
    articles: list = []
    start_page: int = 1
    max_page: int = 1
    api: str = 'https://www.the5fire.com/category/python/'
    host: str = 'https://www.the5fire.com/'
    params: dict = {'page': 1}

    for page in range(start_page, max_page + 1):
        params['page'] = page
        r = await req.get(
            api,
            params=params,
            ssl=False,
            # proxy=proxy,
            retry=1,
            headers={
                'Referer': api,
                'User-Agent': CHROME_PC_UA
            },
        )
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        scode: str = r.content.decode('u8', 'ignore')
        items: list = fromstring(scode).cssselect('#main>.caption')
        if not items:
            break
        if max_page > 1:
            logger.info(
                f'{source} crawling page {page}, + {len(items)} items = {len(articles)} articles'
            )
        for item in items:
            try:
                article: dict = {'source': source}
                title_href = item.cssselect('h3>a')
                title: str = title_href[0].text
                href: str = title_href[0].get('href', '')
                url: str = add_host(href, host)
                desc: str = null_tree.css(item, '.caption>p').text_content()
                raw_time: str = null_tree.css(item, '.info').text_content()
                # 发布：2019-02-22 9:47 p.m.
                raw_time = find_one(r'发布：(\d\d\d\d-\d{1,2}-\d{1,2}.*)',
                                    raw_time)[1].replace('.', '')
                # 2019-03-20 10:07 p.m.
                # 2011-05-28 10 a.m.
                # 2011-12-08 午夜
                if ':' not in raw_time:
                    if 'm' in raw_time:
                        raw_time = re.sub('m.*', 'm', raw_time)
                        ts_publish = ttime(ptime(raw_time,
                                                 fmt='%Y-%m-%d %I %p'))
                    else:
                        raw_time = raw_time[:10]
                        ts_publish = ttime(ptime(raw_time, fmt='%Y-%m-%d'))
                else:
                    ts_publish = ttime(ptime(raw_time, fmt='%Y-%m-%d %I:%M %p'))
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
async def foofish() -> list:
    """Python之禅"""
    source: str = "Python之禅"
    articles: list = []
    start_page: int = 1
    max_page: int = 1
    api: str = 'https://foofish.net/index.html'
    host: str = 'https://foofish.net/'

    for page in range(start_page, max_page + 1):
        if page == 1:
            seed = api
        else:
            seed = api.replace('index.html', f'index{page}.html')
        r = await req.get(
            seed,
            ssl=False,
            # proxy=proxy,
            retry=1,
            headers={
                'Referer': api,
                'User-Agent': CHROME_PC_UA
            },
        )
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        scode: str = r.content.decode('u8', 'ignore')
        container: str = find_one(r'<dl class="dl-horizontal">[\s\S]*?</dl>',
                                  scode)[0]
        if not container:
            logger.error('container not found')
            return articles
        items: list = re.findall(r'<dt>[\S\s]*?</dd>', container)
        if not items:
            break
        if max_page > 1:
            logger.info(
                f'{source} crawling page {page}, + {len(items)} items = {len(articles)} articles'
            )
        for item_html in items:
            try:
                article: dict = {'source': source}
                item = fromstring(item_html)
                title_href = item.cssselect('a')
                title: str = title_href[0].text
                href: str = title_href[0].get('href', '')
                url: str = add_host(href, host)
                raw_time: str = null_tree.css(item, 'dt').text
                ts_publish = ttime(ptime(raw_time, fmt='%Y-%m-%d'))
                article['ts_publish'] = ts_publish
                article['title'] = title
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
async def inventwithpython() -> list:
    """The Invent with Python Blog"""
    source: str = "The Invent with Python Blog"
    articles: list = []
    start_page: int = 1
    max_page: int = 1
    api: str = 'https://inventwithpython.com/blog/index.html'
    host: str = 'https://inventwithpython.com/'

    for page in range(start_page, max_page + 1):
        if page == 1:
            seed = api
        else:
            seed = api.replace('index.html', f'index{page}.html')
        r = await req.get(
            seed,
            ssl=False,
            # proxy=proxy,
            retry=1,
            headers={
                'Referer': api,
                'User-Agent': CHROME_PC_UA
            },
        )
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        scode: str = r.content.decode('u8', 'ignore')
        items: list = fromstring(scode).cssselect('#content>article')
        if not items:
            break
        if max_page > 1:
            logger.info(
                f'{source} crawling page {page}, + {len(items)} items = {len(articles)} articles'
            )
        for item in items:
            try:
                article: dict = {'source': source}
                title_href = null_tree.css(item, 'h1>a')
                title: str = title_href.text
                href: str = title_href.get('href', '')
                url: str = add_host(href, host)
                raw_time: str = null_tree.css(
                    item, '.article-header-date').text.strip()
                # Wed 05 June 2019
                ts_publish = ttime(ptime(raw_time, fmt='%a %d %B %Y'))
                article['ts_publish'] = ts_publish
                article['title'] = title
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
async def lucumr() -> list:
    """Armin Ronacher's Thoughts and Writings"""
    source: str = "Armin Ronacher's Thoughts and Writings"
    articles: list = []
    start_page: int = 1
    max_page: int = 1
    api: str = 'http://lucumr.pocoo.org/'
    host: str = 'http://lucumr.pocoo.org/'

    for page in range(start_page, max_page + 1):
        if page == 1:
            seed = api
        else:
            seed = add_host(f'/page/{page}/', host)
        r = await req.get(
            seed,
            ssl=False,
            # proxy=proxy,
            retry=1,
            headers={
                'Referer': api,
                'User-Agent': CHROME_PC_UA
            },
        )
        if not r:
            logger.error(f'{source} crawl failed: {r}, {r.text}')
            return articles
        scode: str = r.content.decode('u8', 'ignore')
        items: list = fromstring(scode).cssselect(
            '.entry-wrapper>.entry-overview')
        if not items:
            break
        if max_page > 1:
            logger.info(
                f'{source} crawling page {page}, + {len(items)} items = {len(articles)} articles'
            )
        for item in items:
            try:
                article: dict = {'source': source}
                title_href = null_tree.css(item, 'h1>a')
                title: str = title_href.text
                href: str = title_href.get('href', '')
                url: str = add_host(href, host)
                desc: str = null_tree.css(item, '.summary>p').text
                raw_time: str = null_tree.css(item, '.date').text.strip()
                # Jun 5, 2017
                ts_publish = ttime(ptime(raw_time, fmt='%b %d, %Y'))
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
# @register_history
# @register_test
async def treyhunner() -> list:
    """Trey Hunner"""
    source: str = "Trey Hunner"
    articles: list = []
    limit: int = 5
    api: str = 'https://treyhunner.com/blog/categories/python/'
    host: str = 'https://treyhunner.com/'

    r = await req.get(
        api,
        ssl=False,
        # proxy=proxy,
        retry=1,
        headers={
            'Referer': api,
            'User-Agent': CHROME_PC_UA
        },
    )
    if not r:
        logger.error(f'{source} crawl failed: {r}, {r.text}')
        return articles
    scode: str = r.content.decode('u8', 'ignore')
    items: list = fromstring(scode).cssselect('#blog-archives>article')
    for item in items[:limit]:
        try:
            article: dict = {'source': source}
            title_href = null_tree.css(item, 'h1>a')
            title: str = title_href.text
            href: str = title_href.get('href', '')
            url: str = add_host(href, host)
            raw_time: str = null_tree.css(item, 'time').get('datetime')
            # 2019-06-18T09:15:00-07:00
            ts_publish = ttime(ptime(raw_time.replace('T', ' ')[:19], tzone=-7))
            article['ts_publish'] = ts_publish
            article['title'] = title
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
async def reddit() -> list:
    """Reddit"""
    source: str = "Reddit"
    articles: list = []
    limit: int = 10
    # 有 20 赞以上的才收录
    min_ups: int = 20
    # api doc: https://www.reddit.com/dev/api/#GET_top
    api: str = f'https://api.reddit.com/r/Python/top/?t=day&limit={limit}'
    host: str = 'https://www.reddit.com/'

    scode = await outlands_request({
        'method': 'get',
        'url': api,
    }, 'u8')
    if not scode:
        logger.error(f'{source} crawl failed')
        return articles
    rj: dict = json.loads(scode)
    items: list = rj['data']['children']
    for item in items:
        try:
            if item['kind'] != 't3':
                continue
            data = item['data']
            if (data.get('ups') or 0) < min_ups:
                continue
            article: dict = {'source': source}
            title: str = data['title']
            href: str = data['permalink']
            url: str = add_host(href, host)
            raw_time: str = data['created_utc']
            # 1564420248
            ts_publish = ttime(raw_time, tzone=0)
            desc: str = data.get('author') or ''
            article['ts_publish'] = ts_publish
            article['title'] = title
            article['url'] = url
            article['desc'] = desc
            article['url_key'] = get_url_key(article['url'])
            articles.append(article)
        except Exception:
            logger.error(f'{source} crawl failed: {traceback.format_exc()}')
            break
    logger.info(
        f'crawled {len(articles)} articles [{source}]{" ?????????" if not articles else ""}'
    )
    return articles
