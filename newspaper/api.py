#! python3

import pathlib

from starlette.applications import Starlette
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from .config import init_db, global_configs
from .loggers import logger

static_dir = pathlib.Path(__file__).absolute().parent / 'static'
templates_dir = pathlib.Path(__file__).absolute().parent / 'templates'

app = Starlette()
app.mount('/static', StaticFiles(directory=str(static_dir)), name='static')
app.config = global_configs
app.logger = logger
app.db = init_db()
app.templates = Jinja2Templates(directory=str(templates_dir))


@app.on_event('startup')
async def _ensure_article_table_exists():
    await app.db._ensure_article_table_exists()
