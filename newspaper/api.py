#! python3

import pathlib

from starlette.applications import Starlette
from starlette.staticfiles import StaticFiles

from .config import logger, db, global_configs

static_dir = pathlib.Path(__file__).parent / 'static'
templates_dir = pathlib.Path(__file__).parent / 'templates'

app = Starlette(template_directory=str(templates_dir))
app.mount('/static', StaticFiles(directory=str(static_dir)), name='static')
app.config = global_configs
app.logger = logger
app.db = db


@app.on_event('startup')
async def _ensure_article_table_exists():
    await app.db._ensure_article_table_exists()
