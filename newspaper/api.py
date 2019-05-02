#! python3

import pathlib
import traceback

import responder

from .config import api_logger, global_configs

static_dir = pathlib.Path(__file__).parent / 'static'
templates_dir = pathlib.Path(__file__).parent / 'templates'

api = responder.API(static_dir=static_dir,
                    static_route='static',
                    templates_dir=templates_dir)
api.config = global_configs
api.logger = api_logger
