#! python3

import pathlib
import traceback

import responder

from .config import init_logger, global_configs

api = responder.API(
    static_dir=pathlib.Path(__file__).parent / 'static',
    static_route='static',
    templates_dir=pathlib.Path(__file__).parent / 'templates')
api.config = global_configs

init_logger(api)
