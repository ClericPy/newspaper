import traceback

from responder import Response

from .api import api


def handle_pagination_response(url: str, result: dict) -> dict:
    if result.get('has_more'):
        # 翻页地址
        result['next_url'] = ''
    if result['offset'] > 0:
        new_offset = max((result['offset'] - result['limit'], 0))
        result['prev_url'] = ''
    return result


def handle_exception_response(req, resp, err):
    err_string = f'{err.__class__.__name__}: {str(err)}'
    api.logger.error(f"bad response: {req.url}, {err_string}.\n{err.format_exc}")
    resp.media = {"ok": False, "error": err_string}


@api.route("/newspaper/articles.query")
async def index(req, resp):
    # TODO 因为 responder 坑爹的没继承 add_exception_handler, 只能自己拼 json 了...
    params = dict(req.params.items())
    try:
        result = await api.db.query_articles(**params)
        resp.media = handle_pagination_response(req.url, result)
    except Exception as err:
        err.format_exc = traceback.format_exc()
        handle_exception_response(req, resp, err)
