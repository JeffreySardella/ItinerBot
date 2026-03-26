# tests/test_alerts.py
import pytest
from datetime import datetime, date
from alerts import (
    is_ticket_event,
    get_alert_time,
    should_send_nightly,
)


def test_is_ticket_event_before_trip():
    assert is_ticket_event("2026-04-15T10:00:00", date(2026, 5, 26)) is True


def test_is_ticket_event_on_trip():
    assert is_ticket_event("2026-05-26T10:00:00", date(2026, 5, 26)) is False


def test_is_ticket_event_after_trip():
    assert is_ticket_event("2026-05-28T10:00:00", date(2026, 5, 26)) is False


def test_is_ticket_event_all_day():
    assert is_ticket_event("2026-04-15", date(2026, 5, 26)) is True


def test_get_alert_time_from_resolved():
    event = {
        "start_time": "2026-04-15",
        "resolved_time": "2026-04-15T10:00:00",
        "is_all_day": 1,
    }
    result = get_alert_time(event)
    assert result == datetime(2026, 4, 15, 10, 0, 0)


def test_get_alert_time_from_start():
    event = {
        "start_time": "2026-04-15T10:00:00",
        "resolved_time": None,
        "is_all_day": 0,
    }
    result = get_alert_time(event)
    assert result == datetime(2026, 4, 15, 10, 0, 0)


def test_get_alert_time_all_day_no_resolved():
    event = {
        "start_time": "2026-04-15",
        "resolved_time": None,
        "is_all_day": 1,
    }
    result = get_alert_time(event)
    assert result is None


def test_should_send_nightly_within_range():
    today = date(2026, 5, 26)
    trip_end = date(2026, 6, 1)
    assert should_send_nightly(today, trip_end) is True


def test_should_send_nightly_on_end_date():
    today = date(2026, 6, 1)
    trip_end = date(2026, 6, 1)
    assert should_send_nightly(today, trip_end) is True


def test_should_send_nightly_after_end():
    today = date(2026, 6, 2)
    trip_end = date(2026, 6, 1)
    assert should_send_nightly(today, trip_end) is False
