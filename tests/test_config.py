# tests/test_config.py
import os
import pytest
from datetime import date


def test_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "test-token")
    monkeypatch.setenv("CHANNEL_ID", "123456")
    monkeypatch.setenv("TRIP_START_DATE", "2026-05-26")
    monkeypatch.setenv("TRIP_END_DATE", "2026-06-01")
    monkeypatch.setenv("TIMEZONE", "America/Los_Angeles")
    monkeypatch.setenv("GOOGLE_CREDENTIALS", "creds.json")
    monkeypatch.setenv("SERPAPI_KEY", "serpkey")

    import importlib
    import config
    importlib.reload(config)

    assert config.DISCORD_TOKEN == "test-token"
    assert config.CHANNEL_ID == 123456
    assert config.TRIP_START_DATE == date(2026, 5, 26)
    assert config.TRIP_END_DATE == date(2026, 6, 1)
    assert config.TIMEZONE == "America/Los_Angeles"
    assert config.GOOGLE_CREDENTIALS == "creds.json"
    assert config.SERPAPI_KEY == "serpkey"


def test_trip_start_before_end(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "t")
    monkeypatch.setenv("CHANNEL_ID", "1")
    monkeypatch.setenv("TRIP_START_DATE", "2026-06-01")
    monkeypatch.setenv("TRIP_END_DATE", "2026-05-26")
    monkeypatch.setenv("TIMEZONE", "UTC")
    monkeypatch.setenv("GOOGLE_CREDENTIALS", "c.json")
    monkeypatch.setenv("SERPAPI_KEY", "s")

    import importlib
    import config
    with pytest.raises(ValueError, match="TRIP_START_DATE must be before TRIP_END_DATE"):
        importlib.reload(config)
