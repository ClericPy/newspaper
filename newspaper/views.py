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


@api.route("/newspaper/articles.query")
async def index(req, resp):
    # TODO 因为 responder 坑爹的没继承 add_exception_handler, 只能自己拼 json 了...
    params = dict(req.params.items())
    try:
        result = await api.db.query_articles(**params)
        resp.media = handle_pagination_response(req.full_url, result)
    except Exception as err:
        err.format_exc = traceback.format_exc()
        handle_exception_response(req, resp, err)
