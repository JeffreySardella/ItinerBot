# tests/test_calendar_sync.py
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from calendar_sync import CalendarSync


def make_gcal_event(event_id, summary, start, end, all_day=False):
    """Helper to create a Google Calendar API event dict."""
    if all_day:
        return {
            "id": event_id,
            "summary": summary,
            "start": {"date": start},
            "end": {"date": end},
            "description": "",
            "location": "",
        }
    return {
        "id": event_id,
        "summary": summary,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
        "description": "",
        "location": "",
    }


def test_parse_timed_event():
    gcal_event = make_gcal_event(
        "e1", "Dinner", "2026-05-27T18:00:00-07:00", "2026-05-27T20:00:00-07:00"
    )
    sync = CalendarSync.__new__(CalendarSync)
    parsed = sync._parse_event(gcal_event)
    assert parsed["event_id"] == "e1"
    assert parsed["title"] == "Dinner"
    assert parsed["is_all_day"] == 0
    assert "18:00:00" in parsed["start_time"]


def test_parse_all_day_event():
    gcal_event = make_gcal_event("e2", "Buy Tix", "2026-04-15", "2026-04-16", all_day=True)
    sync = CalendarSync.__new__(CalendarSync)
    parsed = sync._parse_event(gcal_event)
    assert parsed["event_id"] == "e2"
    assert parsed["title"] == "Buy Tix"
    assert parsed["is_all_day"] == 1
    assert parsed["start_time"] == "2026-04-15"


def test_parse_event_missing_optional_fields():
    gcal_event = {
        "id": "e3",
        "summary": "Quick thing",
        "start": {"dateTime": "2026-05-28T10:00:00-07:00"},
        "end": {"dateTime": "2026-05-28T11:00:00-07:00"},
    }
    sync = CalendarSync.__new__(CalendarSync)
    parsed = sync._parse_event(gcal_event)
    assert parsed["description"] == ""
    assert parsed["location"] == ""
