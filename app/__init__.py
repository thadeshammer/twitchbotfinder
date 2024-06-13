# app/__init__.py
import logging.config
import os
from typing import List, Union

import yaml
from flask import Flask

from app.db import Base, engine, init_db

from .config import Config, ConfigKey
from .models import observation, suspect, twitch_user_data
from .routes import register_routes


def extract_filenames_from_logger_config(logger_config: dict) -> list:
    filenames = []

    for handler in logger_config.get("handlers", {}).values():
        if "filename" in handler:
            filenames.append(handler["filename"])

    return filenames


def setup_logging() -> None:
    path: str = Config.LOGGING_CONFIG_FILE

    if os.path.exists(path):
        with open(path, "rt", encoding="UTF8") as config_file:
            config: Union[List, dict, None] = yaml.safe_load(config_file.read())
            assert isinstance(config, dict)
            logging.config.dictConfig(config)

            log_files: list = extract_filenames_from_logger_config(config)

            print(f"Log file(s) are at: {log_files}", flush=True)
    else:
        print("Log config not found, using defaults.", flush=True)
        logging.basicConfig(level=logging.DEBUG)


def tee_up_database(app: Flask):
    database_uri: str = app.config[ConfigKey.SQLALCHEMY_DATABASE_URI]
    max_retries: int = app.config[ConfigKey.SQLALCHEMY_CONNECT_MAX_RETRIES]
    retry_interval: int = app.config[ConfigKey.SQLALCHEMY_CONNECT_RETRY_INTERVAL]
    init_db(database_uri, max_retries, retry_interval)


def create_app() -> Flask:
    app: Flask = Flask(__name__)

    Config.load_secrets()
    app.config.from_object(Config)
    app.debug = False

    setup_logging()
    logger = logging.getLogger("app")
    logger.info("Logger is ready.")

    tee_up_database(app)

    with app.app_context():
        register_routes(app)
        Base.metadata.create_all(bind=engine)
    return app
