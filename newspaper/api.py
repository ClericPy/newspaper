#! python3

import pathlib

import responder

from .config import logger, db, global_configs

static_dir = pathlib.Path(__file__).parent / 'static'
templates_dir = pathlib.Path(__file__).parent / 'templates'

api = responder.API(static_dir=static_dir,
                    static_route='static',
                    templates_dir=templates_dir)
api.config = global_configs
api.logger = logger
api.db = db


@api.on_event('startup')
async def _ensure_article_table_exists():
    await api.db._ensure_article_table_exists()
