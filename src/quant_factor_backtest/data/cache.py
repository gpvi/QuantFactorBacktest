from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class CacheBackend(Protocol):
    def get(self, key: str) -> list[dict]:
        ...

    def set(self, key: str, value: list[dict]) -> None:
        ...


class SqlJsonCache(ABC):
    table_name = "cache_entries"

    def get(self, key: str) -> list[dict]:
        with self._connect() as connection:
            self._ensure_schema(connection)
            row = connection.execute(
                f"SELECT value_json FROM {self.table_name} WHERE cache_key = ?",
                (key,),
            ).fetchone()
        if row is None:
            raise KeyError(key)
        return json.loads(row[0])

    def set(self, key: str, value: list[dict]) -> None:
        payload = json.dumps(value, ensure_ascii=True)
        with self._connect() as connection:
            self._ensure_schema(connection)
            self._upsert(connection, key, payload)
            connection.commit()

    def _ensure_schema(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                cache_key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL
            )
            """
        )

    def _upsert(self, connection: sqlite3.Connection, key: str, payload: str) -> None:
        connection.execute(
            f"""
            INSERT INTO {self.table_name} (cache_key, value_json)
            VALUES (?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET value_json = excluded.value_json
            """,
            (key, payload),
        )

    @abstractmethod
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError


@dataclass(frozen=True)
class SqliteCache(SqlJsonCache):
    db_path: str

    def __post_init__(self) -> None:
        with self._connect() as connection:
            self._ensure_schema(connection)
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(path)


@dataclass(frozen=True)
class FileCache:
    root_dir: str

    def get(self, key: str) -> list[dict]:
        path = self._path_for(key)
        if not path.exists():
            raise KeyError(key)
        return json.loads(path.read_text(encoding="utf-8"))

    def set(self, key: str, value: list[dict]) -> None:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=True), encoding="utf-8")

    def _path_for(self, key: str) -> Path:
        return Path(self.root_dir) / f"{key}.json"


class NullCache:
    def get(self, key: str) -> list[dict]:
        raise KeyError(key)

    def set(self, key: str, value: list[dict]) -> None:
        return None
