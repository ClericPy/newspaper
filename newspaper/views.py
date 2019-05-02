from .api import api


@api.route("/")
async def index(req, resp):
    resp.text = "ok"
