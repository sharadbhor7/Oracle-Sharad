from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from .config import DatabaseConfig


class OracleDatabase:
    def __init__(self, config: DatabaseConfig):
        self.config = config

    @contextmanager
    def connect(self) -> Iterator[object]:
        import oracledb

        if self.config.mode == "thick":
            oracledb.init_oracle_client()
        connection = oracledb.connect(
            user=self.config.user,
            password=self.config.password,
            dsn=self.config.dsn,
        )
        try:
            yield connection
        finally:
            connection.close()
