import unittest
from pathlib import Path
from uuid import uuid4

from quant_factor_backtest.data import FileCache, NullCache, SqliteCache, TushareConfig, TushareDataClient


class FakeFrame:
    def __init__(self, records):
        self._records = records

    def to_dict(self, orient):
        if orient != "records":
            raise ValueError("unsupported orient")
        return self._records


class FakeProClient:
    def __init__(self):
        self.daily_calls = 0
        self.daily_basic_calls = 0
        self.adj_factor_calls = 0

    def daily(self, trade_date=None, ts_code=None, fields="", start_date=None, end_date=None):
        self.daily_calls += 1
        if start_date and end_date:
            return FakeFrame(
                [
                    {"ts_code": "000001.SZ", "trade_date": "20240102", "close": 10.0, "amount": 2000000.0},
                    {"ts_code": "000002.SZ", "trade_date": "20240102", "close": 20.0, "amount": 500000.0},
                    {"ts_code": "000001.SZ", "trade_date": "20240103", "close": 11.0, "amount": 2100000.0},
                    {"ts_code": "000002.SZ", "trade_date": "20240103", "close": 22.0, "amount": 600000.0},
                ]
            )
        return FakeFrame([])

    def adj_factor(self, trade_date=None, ts_code=None, fields="", start_date=None, end_date=None):
        self.adj_factor_calls += 1
        if start_date and end_date:
            return FakeFrame(
                [
                    {"ts_code": "000001.SZ", "trade_date": "20240102", "adj_factor": 1.1},
                    {"ts_code": "000002.SZ", "trade_date": "20240102", "adj_factor": 0.9},
                    {"ts_code": "000001.SZ", "trade_date": "20240103", "adj_factor": 1.1},
                    {"ts_code": "000002.SZ", "trade_date": "20240103", "adj_factor": 0.95},
                ]
            )
        return FakeFrame([])

    def daily_basic(self, trade_date=None, fields="", start_date=None, end_date=None):
        self.daily_basic_calls += 1
        if start_date and end_date:
            return FakeFrame(
                [
                    {"ts_code": "000001.SZ", "trade_date": "20240102", "pe": 10.0, "pb": 1.2, "total_mv": 100.0},
                    {"ts_code": "000001.SZ", "trade_date": "20240103", "pe": 10.0, "pb": 1.2, "total_mv": 100.0},
                ]
            )
        return FakeFrame(
            [
                {"ts_code": "000001.SZ", "trade_date": trade_date, "pe": 10.0, "pb": 1.2, "total_mv": 100.0},
            ]
        )


class InMemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, list[dict]] = {}
        self.get_calls: list[str] = []
        self.set_calls: list[str] = []

    def get(self, key: str) -> list[dict]:
        self.get_calls.append(key)
        if key not in self._store:
            raise KeyError(key)
        return self._store[key]

    def set(self, key: str, value: list[dict]) -> None:
        self.set_calls.append(key)
        self._store[key] = value


class CacheBackendTest(unittest.TestCase):
    def test_default_cache_backend_uses_null_cache_when_cache_dir_disabled(self) -> None:
        client = TushareDataClient(
            config=TushareConfig(token="test-token", cache_dir=None),
            pro_client=FakeProClient(),
        )

        self.assertIsInstance(client._cache, NullCache)

    def test_default_cache_backend_uses_sqlite_cache_when_cache_dir_enabled(self) -> None:
        temp_path = Path(".cache") / "tests" / f"default_sqlite_cache_{uuid4().hex}"
        temp_path.mkdir(parents=True, exist_ok=True)
        try:
            client = TushareDataClient(
                config=TushareConfig(token="test-token", cache_dir=str(temp_path)),
                pro_client=FakeProClient(),
            )

            self.assertIsInstance(client._cache, SqliteCache)
            self.assertTrue(client._cache.db_path.endswith("cache.sqlite3"))
            self.assertTrue((temp_path / "cache.sqlite3").exists())
        finally:
            if temp_path.exists():
                for path in sorted(temp_path.rglob("*"), reverse=True):
                    try:
                        if path.is_file():
                            path.unlink()
                        elif path.is_dir():
                            path.rmdir()
                    except PermissionError:
                        pass
                try:
                    temp_path.rmdir()
                except OSError:
                    pass

    def test_cache_backend_can_be_injected_for_future_extensions(self) -> None:
        pro_client = FakeProClient()
        cache = InMemoryCache()
        client = TushareDataClient(
            config=TushareConfig(token="test-token", cache_dir=None),
            pro_client=pro_client,
            cache_backend=cache,
        )

        first = client.fetch_daily_basic(trade_date="20240102")
        second = client.fetch_daily_basic(trade_date="20240102")

        self.assertEqual(first, second)
        self.assertEqual(pro_client.daily_basic_calls, 1)
        self.assertTrue(any(key.startswith("daily_basic/20240102__all__") for key in cache._store))

    def test_batch_fetch_uses_cached_dates_and_only_fetches_missing_ones(self) -> None:
        pro_client = FakeProClient()
        cache = InMemoryCache()
        cache.set(
            "daily_basic/20240102__all__ts_code_trade_date_pb",
            [{"ts_code": "000001.SZ", "trade_date": "20240102", "pb": 1.2}],
        )
        cache.set_calls.clear()
        client = TushareDataClient(
            config=TushareConfig(token="test-token", cache_dir=None),
            pro_client=pro_client,
            cache_backend=cache,
        )

        signal = client.fetch_factor_signal(
            trade_dates=["20240102", "20240103"],
            field="pb",
            factor_name="pb_factor",
        )

        self.assertEqual(signal.values["20240102"]["000001.SZ"], 1.2)
        self.assertEqual(signal.values["20240103"]["000001.SZ"], 1.2)
        self.assertEqual(pro_client.daily_basic_calls, 1)
        self.assertIn("daily_basic/20240103__all__ts_code_trade_date_pb", cache.set_calls)
        self.assertNotIn("daily_basic/20240102__all__ts_code_trade_date_pb", cache.set_calls)

    def test_batch_fetch_writes_each_missing_date_into_cache(self) -> None:
        pro_client = FakeProClient()
        cache = InMemoryCache()
        client = TushareDataClient(
            config=TushareConfig(token="test-token", cache_dir=None),
            pro_client=pro_client,
            cache_backend=cache,
        )

        client.fetch_market_data(
            trade_dates=["20240102", "20240103"],
            ts_codes=["000001.SZ", "000002.SZ"],
        )

        self.assertEqual(pro_client.daily_calls, 1)
        self.assertEqual(pro_client.adj_factor_calls, 1)
        self.assertIn("daily/20240102__000001_SZ_000002_SZ__ts_code_trade_date_close_amount", cache._store)
        self.assertIn("daily/20240103__000001_SZ_000002_SZ__ts_code_trade_date_close_amount", cache._store)
        self.assertIn("adj_factor/20240102__000001_SZ_000002_SZ__ts_code_trade_date_adj_factor", cache._store)
        self.assertIn("adj_factor/20240103__000001_SZ_000002_SZ__ts_code_trade_date_adj_factor", cache._store)


class FileCacheTest(unittest.TestCase):
    def test_file_cache_uses_stable_string_keys(self) -> None:
        temp_path = Path(".cache") / "tests" / f"file_cache_{uuid4().hex}"
        temp_path.mkdir(parents=True, exist_ok=True)
        try:
            cache = FileCache(root_dir=str(temp_path))
            cache.set("daily/20240102__000001_SZ__ts_code_trade_date_close", [{"ts_code": "000001.SZ"}])

            records = cache.get("daily/20240102__000001_SZ__ts_code_trade_date_close")

            self.assertEqual(records[0]["ts_code"], "000001.SZ")
            self.assertTrue(
                (temp_path / "daily" / "20240102__000001_SZ__ts_code_trade_date_close.json").exists()
            )
        finally:
            if temp_path.exists():
                for path in sorted(temp_path.rglob("*"), reverse=True):
                    try:
                        if path.is_file():
                            path.unlink()
                        elif path.is_dir():
                            path.rmdir()
                    except PermissionError:
                        pass
                try:
                    temp_path.rmdir()
                except OSError:
                    pass


class SqliteCacheTest(unittest.TestCase):
    def test_sqlite_cache_uses_stable_string_keys(self) -> None:
        temp_path = Path(".cache") / "tests" / f"sqlite_cache_{uuid4().hex}"
        temp_path.mkdir(parents=True, exist_ok=True)
        db_path = temp_path / "cache.sqlite3"
        try:
            cache = SqliteCache(db_path=str(db_path))
            cache.set("daily/20240102__000001_SZ__ts_code_trade_date_close", [{"ts_code": "000001.SZ"}])

            records = cache.get("daily/20240102__000001_SZ__ts_code_trade_date_close")

            self.assertEqual(records[0]["ts_code"], "000001.SZ")
            self.assertTrue(db_path.exists())
        finally:
            if temp_path.exists():
                for path in sorted(temp_path.rglob("*"), reverse=True):
                    try:
                        if path.is_file():
                            path.unlink()
                        elif path.is_dir():
                            path.rmdir()
                    except PermissionError:
                        pass
                try:
                    temp_path.rmdir()
                except OSError:
                    pass


if __name__ == "__main__":
    unittest.main()
