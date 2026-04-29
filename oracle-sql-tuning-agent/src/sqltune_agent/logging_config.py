from __future__ import annotations

import logging

from .config import LoggingConfig


def configure_logging(config: LoggingConfig) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if config.file:
        handlers.append(logging.FileHandler(config.file, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, config.level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=handlers,
    )
