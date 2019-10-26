import json
import re
import traceback
from urllib.parse import urlencode

from starlette.responses import (JSONResponse, PlainTextResponse,
                                 RedirectResponse, Response)
from torequests.utils import ptime, time, ttime

from .api import app
from .config import ONLINE_HOST, GA_ID
from .crawler.sources import content_sources_dict
from .loggers import log_dir
from .utils import gen_rss, tail_file


class APIError(Exception):
    pass


def handle_pagination_response(url: str, result: dict) -> dict:
    base_url = re.sub(r'^https?://[^/]+|\?.*', '', url)
    result['ok'] = True
    params = {
        k: v
        for k, v in sorted(result.items(), key=lambda x: x[0])
        if k not in {'articles', 'has_more', 'next_url', 'prev_url', 'ok'}
    }
    prev_offset = max((result['offset'] - result['limit'], 0))
    next_offset = result['offset'] + result['limit']
    if result['offset'] > 0:
        # 前页地址
        params['offset'] = prev_offset
        result['prev_url'] = f'{base_url}?{urlencode(params)}'
    if result.get('has_more'):
        # 后页地址
        params['offset'] = next_offset
        result['next_url'] = f'{base_url}?{urlencode(params)}'
    return result


@app.exception_handler(Exception)
def handle_default_exception(req, error):
    """非 API 错误的捕获, 会被下面的 API 错误覆盖"""
    err_string = f'{error.__class__.__name__}: {str(error)}'
    app.logger.error(f"{str(req.url)}, {err_string}.\n{traceback.format_exc()}")
    # 避免泄漏信息, 只输出错误类型
    return JSONResponse({"ok": False, "error": error.__class__.__name__})


@app.exception_handler(APIError)
def handle_api_error(req, error):
    """只捕获主动 raise 出来的 API error"""
    err_string = str(error)
    app.logger.error(
        f"{str(req.url)}, APIError: {err_string}.\n{traceback.format_exc()}")
    # APIError 一般不会带上敏感信息
    return JSONResponse({"ok": False, "error": err_string})


@app.route('/')
async def index(req):
    return RedirectResponse('/newspaper/articles.query.html', 302)


@app.route("/newspaper/articles.cache.clear")
async def articles_query_cache_clear(req):
    if req.client.host == '127.0.0.1':
        app.db.query_articles.cache_clear()
        return PlainTextResponse('ok')
    else:
        return PlainTextResponse('fail')


@app.route("/newspaper/logs/spider")
async def spider_log(req):
    """只允许查看 spider log, 其他的信息不对外开放"""
    fp = log_dir / 'spider.log'
    size = req.query_params.get('size') or req.query_params.get('s')
    if size:
        size = int(size)
    else:
        size = len([
            i for i in content_sources_dict.values() if i['status'] == '√'
        ]) * 120
    text = await tail_file(fp, size)
    return PlainTextResponse(text)


@app.route('/favicon.ico')
async def redirect_ico(req):
    return RedirectResponse('/static/favicon.ico', 301)


@app.route("/newspaper/articles.query.{output}")
async def articles_query(req):
    """搜索文章
    output 支持: html(默认), json, rss

    支持参数:
    query: str = None,
    start_time: str = "",
    end_time: str = "",
    source: str = "",
    order_by: str = 'ts_create',
    sorting: str = 'desc',
    limit: int = 10,
    offset: int = 0
    """
    output = req.path_params['output']
    if output == 'json':
        params = dict(req.query_params)
        result = await app.db.query_articles(**params)
        return JSONResponse(handle_pagination_response(req.url._url, result))
    elif output == 'html':
        return app.templates.TemplateResponse('articles.html', {
            "request": req,
            "GA_ID": GA_ID
        })
    elif output == 'rss':
        # 只保留日报的 RSS 接口, 不再对 Timeline 做 rss 了, 没有必要
        # https://www.clericpy.top/newspaper/daily.python.list.rss.any
        params = dict(req.query_params)
        lang = params.get('lang', 'any').lower()
        return RedirectResponse(f'/newspaper/daily.python.list.rss.{lang}', 302)
    else:
        return PlainTextResponse("NotImplemented")


@app.route("/newspaper/daily.python/{date}")
async def daily_python(req):
    """Python 日报, 按 date 取文章, 以后考虑支持更多参数(过滤订阅源, 过滤 level, 过滤中英文)"""
    date = req.path_params['date']
    params = dict(req.query_params)
    # 默认按发布时间
    params.setdefault('order_by', 'ts_publish')
    result = await app.db.query_articles(date=date, **params)
    return app.templates.TemplateResponse(
        'daily_python.html', {
            "request": req,
            "articles": json.dumps(result).replace('`', "'"),
            "title": date,
            "GA_ID": GA_ID
        })


@app.route("/newspaper/daily.python.list.rss.{language}")
async def daily_python_list(req):
    """Python 日报列表, 其实就是个按照日期伪造的页面, 用来订阅 rss"""
    language = req.path_params['language'].lower()
    if language not in {'cn', 'en', 'any'}:
        return PlainTextResponse('language should be cn / en / any.')
    limit: int = int(req.query_params.get('limit') or 10)
    xml_data: dict = {
        'channel': {
            'title': 'Python Daily',
            'description': 'Python Daily Newspaper',
            'link': f'https://{ONLINE_HOST}/newspaper/daily.python.list.rss.{language}',
            'language': {
                'cn': 'zh-cn',
                'any': 'zh-cn'
            }.get(language, 'en'),
        },
        'items': []
    }
    for date_delta in range(1, limit):
        title_date: str = ttime(time.time() - 86400 * date_delta)[:10]
        # 当日 0 点发布前一天的结果
        pubDate: str = ttime(ptime(ttime(time.time() - 86400 *
                                         (date_delta - 1))[:10],
                                   fmt='%Y-%m-%d'),
                             fmt='%a, %d %b %Y')
        link: str = f'https://{ONLINE_HOST}/newspaper/daily.python/{title_date}?lang={language}'
        item: dict = {
            'title': f'Python Daily [{title_date}]',
            'link': link,
            'guid': link,
            'pubDate': pubDate
        }
        xml_data['items'].append(item)
    xml: str = gen_rss(xml_data)
    return Response(xml, media_type='text/xml')


@app.route("/newspaper/source.redirect")
async def source_redirect(req):
    """Python 日报, 按 date 取文章, 以后考虑支持更多参数(过滤订阅源, 过滤 level, 过滤中英文)"""
    name = req.query_params['name']
    return RedirectResponse(
        content_sources_dict.get(name,
                                 {}).get('url',
                                         '/newspaper/articles.query.html'), 302)
