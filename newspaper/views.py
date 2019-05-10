import re
import traceback
from urllib.parse import urlencode

from .api import api


def handle_pagination_response(url: str, result: dict) -> dict:
    base_url = re.sub('\?.*', '', url)
    params = {
        k: v
        for k, v in sorted(result.items(), key=lambda x: x[0])
        if k not in {'articles', 'has_more'}
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


def handle_exception_response(req, resp, err):
    err_string = f'{err.__class__.__name__}: {str(err)}'
    api.logger.error(
        f"bad response: {req.url}, {err_string}.\n{err.format_exc}")
    resp.media = {"ok": False, "error": err_string}


@api.route('/')
async def index(req, resp):
    api.redirect(resp,
                 '/newspaper/articles.query.json',
                 status_code=api.status_codes.HTTP_302)


@api.route("/newspaper/articles.query.{output}")
async def articles_query(req, resp, *, output):
    """搜索文章
    output 支持: html(默认), json, rss

    支持参数:
    query: str = None,
    start_time: str = "",
    end_time: str = "",
    source: str = "",
    order_by: str = 'ts_publish',
    sorting: str = 'desc',
    limit: int = 10,
    offset: int = 0
    """
    # TODO 因为 responder 坑爹的没继承 add_exception_handler, 只能自己拼 json 了...
    try:
        params = dict(req.params.items())
        result = await api.db.query_articles(**params)
        if output == 'json':
            resp.media = handle_pagination_response(req.full_url, result)
        elif output == 'html':
            resp.html = api.template('articles.html')
    except Exception as err:
        err.format_exc = traceback.format_exc()
        handle_exception_response(req, resp, err)


@api.route('/static/favicon.ico')
async def icon(req, resp):
    api.redirect(resp, '/static/favicon.ico')
