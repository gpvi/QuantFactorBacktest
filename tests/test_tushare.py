import unittest
from pathlib import Path
from unittest.mock import patch

from quant_factor_backtest.data import TushareConfig, TushareDataClient
from quant_factor_backtest.factors import DailyBasicFieldFactor


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

    def daily(self, trade_date, ts_code, fields):
        self.daily_calls += 1
        self.last_daily_call = {
            "trade_date": trade_date,
            "ts_code": ts_code,
            "fields": fields,
        }
        if trade_date == "20240102":
            return FakeFrame(
                [
                    {"ts_code": "000001.SZ", "trade_date": "20240102", "close": 10.0, "amount": 2000000.0},
                    {"ts_code": "000002.SZ", "trade_date": "20240102", "close": 20.0, "amount": 500000.0},
                ]
            )
        return FakeFrame(
            [
                {"ts_code": "000001.SZ", "trade_date": "20240103", "close": 11.0, "amount": 2100000.0},
                {"ts_code": "000002.SZ", "trade_date": "20240103", "close": 22.0, "amount": 600000.0},
            ]
        )

    def adj_factor(self, trade_date, ts_code, fields):
        self.adj_factor_calls += 1
        if trade_date == "20240102":
            return FakeFrame(
                [
                    {"ts_code": "000001.SZ", "trade_date": "20240102", "adj_factor": 1.1},
                    {"ts_code": "000002.SZ", "trade_date": "20240102", "adj_factor": 0.9},
                ]
            )
        return FakeFrame(
            [
                {"ts_code": "000001.SZ", "trade_date": "20240103", "adj_factor": 1.1},
                {"ts_code": "000002.SZ", "trade_date": "20240103", "adj_factor": 0.95},
            ]
        )

    def daily_basic(self, trade_date, fields):
        self.daily_basic_calls += 1
        return FakeFrame(
            [
                {"ts_code": "000001.SZ", "trade_date": trade_date, "pe": 10.0, "pb": 1.2, "total_mv": 100.0},
            ]
        )

    def stock_basic(self, exchange="", list_status="L", fields="ts_code,name,list_date"):
        return FakeFrame(
            [
                {"ts_code": "000001.SZ", "name": "PingAn", "list_date": "20000101"},
                {"ts_code": "000002.SZ", "name": "*ST Vanke", "list_date": "20231215"},
            ]
        )

    def suspend_d(self, trade_date, fields="ts_code,trade_date,suspend_type"):
        if trade_date == "20240102":
            return FakeFrame(
                [
                    {"ts_code": "000002.SZ", "trade_date": trade_date, "suspend_type": "S"},
                ]
            )
        return FakeFrame([])

    def stk_limit(self, trade_date, ts_code, fields="ts_code,trade_date,up_limit,down_limit"):
        if trade_date == "20240102":
            return FakeFrame(
                [
                    {"ts_code": "000001.SZ", "trade_date": trade_date, "up_limit": 11.0, "down_limit": 9.0},
                    {"ts_code": "000002.SZ", "trade_date": trade_date, "up_limit": 20.0, "down_limit": 18.0},
                ]
            )
        return FakeFrame(
            [
                {"ts_code": "000001.SZ", "trade_date": trade_date, "up_limit": 12.1, "down_limit": 9.9},
                {"ts_code": "000002.SZ", "trade_date": trade_date, "up_limit": 24.2, "down_limit": 19.8},
            ]
        )


class TushareDataClientTest(unittest.TestCase):
    @patch.dict("os.environ", {"TUSHARE_TOKEN": "env-token"}, clear=True)
    def test_config_from_env_reads_tushare_token(self) -> None:
        config = TushareConfig.from_env()

        self.assertEqual(config.token, "env-token")
        self.assertEqual(config.adj, "qfq")

    def test_fetch_market_data_converts_daily_prices_to_market_data(self) -> None:
        pro_client = FakeProClient()
        client = TushareDataClient(
            config=TushareConfig(token="test-token", adj="qfq"),
            pro_client=pro_client,
        )

        market_data = client.fetch_market_data(
            trade_dates=["20240102", "20240103"],
            ts_codes=["000001.SZ", "000002.SZ"],
        )

        self.assertAlmostEqual(market_data.prices["20240102"]["000001.SZ"], 11.0)
        self.assertAlmostEqual(market_data.prices["20240102"]["000002.SZ"], 18.0)
        self.assertAlmostEqual(market_data.prices["20240103"]["000001.SZ"], 12.1)
        self.assertAlmostEqual(market_data.prices["20240103"]["000002.SZ"], 20.9)

    def test_fetch_daily_basic_returns_records(self) -> None:
        pro_client = FakeProClient()
        client = TushareDataClient(
            config=TushareConfig(token="test-token"),
            pro_client=pro_client,
        )

        records = client.fetch_daily_basic(trade_date="20240102")

        self.assertEqual(records[0]["ts_code"], "000001.SZ")
        self.assertEqual(records[0]["trade_date"], "20240102")
        self.assertEqual(records[0]["pe"], 10.0)

    def test_fetch_factor_signal_builds_cross_section_from_daily_basic_field(self) -> None:
        pro_client = FakeProClient()
        client = TushareDataClient(
            config=TushareConfig(token="test-token"),
            pro_client=pro_client,
        )

        signal = client.fetch_factor_signal(
            trade_dates=["20240102", "20240103"],
            field="pb",
            factor_name="pb_factor",
        )

        self.assertEqual(signal.name, "pb_factor")
        self.assertEqual(signal.values["20240102"]["000001.SZ"], 1.2)
        self.assertEqual(signal.values["20240103"]["000001.SZ"], 1.2)

    def test_fetch_market_data_with_universe_metadata_builds_filter_fields(self) -> None:
        client = TushareDataClient(
            config=TushareConfig(token="test-token"),
            pro_client=FakeProClient(),
        )

        market_data = client.fetch_market_data_with_universe_metadata(
            trade_dates=["20240102", "20240103"],
            ts_codes=["000001.SZ", "000002.SZ"],
        )

        self.assertFalse(market_data.is_st["20240102"]["000001.SZ"])
        self.assertTrue(market_data.is_st["20240102"]["000002.SZ"])
        self.assertFalse(market_data.is_suspended["20240102"]["000001.SZ"])
        self.assertTrue(market_data.is_suspended["20240102"]["000002.SZ"])
        self.assertGreater(market_data.listed_days["20240102"]["000001.SZ"], 1000)
        self.assertLess(market_data.listed_days["20240102"]["000002.SZ"], 60)
        self.assertFalse(market_data.is_limit_up["20240102"]["000001.SZ"])
        self.assertTrue(market_data.is_limit_up["20240102"]["000002.SZ"])
        self.assertEqual(market_data.turnover_amount["20240102"]["000001.SZ"], 2000000.0)

    def test_cache_avoids_repeated_api_calls(self) -> None:
        temp_dir = Path("tests/.cache_test")
        temp_dir.mkdir(parents=True, exist_ok=True)
        try:
            pro_client = FakeProClient()
            client = TushareDataClient(
                config=TushareConfig(token="test-token", cache_dir=str(temp_dir)),
                pro_client=pro_client,
            )

            first = client.fetch_daily_basic(trade_date="20240102")
            second = client.fetch_daily_basic(trade_date="20240102")

            self.assertEqual(first, second)
            self.assertEqual(pro_client.daily_basic_calls, 1)
            cache_files = list(temp_dir.rglob("*.json"))
            self.assertEqual(len(cache_files), 1)
        finally:
            for path in sorted(temp_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            if temp_dir.exists():
                temp_dir.rmdir()


class DailyBasicFieldFactorTest(unittest.TestCase):
    def test_compute_uses_client_to_load_factor_signal(self) -> None:
        client = TushareDataClient(
            config=TushareConfig(token="test-token"),
            pro_client=FakeProClient(),
        )
        factor = DailyBasicFieldFactor(
            name="size",
            field="total_mv",
            trade_dates=["20240102", "20240103"],
            data_client=client,
        )

        signal = factor.compute(market_data=None)

        self.assertEqual(signal.name, "size")
        self.assertEqual(signal.values["20240102"]["000001.SZ"], 100.0)
        self.assertEqual(signal.values["20240103"]["000001.SZ"], 100.0)


if __name__ == "__main__":
    unittest.main()
