# tests/test_database.py
import pytest
import asyncio
from database import Database


@pytest.fixture
def db(tmp_path):
    d = Database(str(tmp_path / "test.db"))
    asyncio.get_event_loop().run_until_complete(d.init())
    yield d
    asyncio.get_event_loop().run_until_complete(d.close())


def test_upsert_and_get_event(db):
    event = {
        "event_id": "abc123",
        "title": "Concert",
        "start_time": "2026-04-15T10:00:00",
        "end_time": "2026-04-15T12:00:00",
        "description": "Live show",
        "location": "Arena",
        "is_all_day": 0,
    }
    asyncio.get_event_loop().run_until_complete(db.upsert_event(event))
    result = asyncio.get_event_loop().run_until_complete(db.get_event("abc123"))
    assert result["title"] == "Concert"
    assert result["alert_night"] == 0
    assert result["lookup_initial"] == 0


def test_get_events_for_date(db):
    e1 = {
        "event_id": "e1", "title": "Morning Hike",
        "start_time": "2026-05-27T08:00:00", "end_time": "2026-05-27T10:00:00",
        "description": "", "location": "", "is_all_day": 0,
    }
    e2 = {
        "event_id": "e2", "title": "Dinner",
        "start_time": "2026-05-27T18:00:00", "end_time": "2026-05-27T20:00:00",
        "description": "", "location": "", "is_all_day": 0,
    }
    e3 = {
        "event_id": "e3", "title": "Other day",
        "start_time": "2026-05-28T10:00:00", "end_time": "2026-05-28T12:00:00",
        "description": "", "location": "", "is_all_day": 0,
    }
    asyncio.get_event_loop().run_until_complete(db.upsert_event(e1))
    asyncio.get_event_loop().run_until_complete(db.upsert_event(e2))
    asyncio.get_event_loop().run_until_complete(db.upsert_event(e3))
    events = asyncio.get_event_loop().run_until_complete(db.get_events_for_date("2026-05-27"))
    assert len(events) == 2
    assert {e["title"] for e in events} == {"Morning Hike", "Dinner"}


def test_update_alert_flag(db):
    event = {
        "event_id": "x1", "title": "Test",
        "start_time": "2026-04-10T09:00:00", "end_time": "2026-04-10T10:00:00",
        "description": "", "location": "", "is_all_day": 0,
    }
    asyncio.get_event_loop().run_until_complete(db.upsert_event(event))
    asyncio.get_event_loop().run_until_complete(db.set_flag("x1", "alert_night", 1))
    result = asyncio.get_event_loop().run_until_complete(db.get_event("x1"))
    assert result["alert_night"] == 1


def test_set_resolved_time(db):
    event = {
        "event_id": "t1", "title": "Buy Concert Tix",
        "start_time": "2026-04-20", "end_time": "2026-04-20",
        "description": "", "location": "", "is_all_day": 1,
    }
    asyncio.get_event_loop().run_until_complete(db.upsert_event(event))
    asyncio.get_event_loop().run_until_complete(db.set_resolved_time("t1", "2026-04-20T10:00:00"))
    result = asyncio.get_event_loop().run_until_complete(db.get_event("t1"))
    assert result["resolved_time"] == "2026-04-20T10:00:00"


def test_delete_removed_events(db):
    e1 = {"event_id": "keep", "title": "Keep", "start_time": "2026-05-01T10:00:00", "end_time": "2026-05-01T12:00:00", "description": "", "location": "", "is_all_day": 0}
    e2 = {"event_id": "remove", "title": "Remove", "start_time": "2026-05-02T10:00:00", "end_time": "2026-05-02T12:00:00", "description": "", "location": "", "is_all_day": 0}
    asyncio.get_event_loop().run_until_complete(db.upsert_event(e1))
    asyncio.get_event_loop().run_until_complete(db.upsert_event(e2))
    asyncio.get_event_loop().run_until_complete(db.delete_events_not_in(["keep"]))
    assert asyncio.get_event_loop().run_until_complete(db.get_event("keep")) is not None
    assert asyncio.get_event_loop().run_until_complete(db.get_event("remove")) is None


def test_get_all_events(db):
    e1 = {"event_id": "a1", "title": "First", "start_time": "2026-04-15T10:00:00", "end_time": "2026-04-15T10:30:00", "description": "", "location": "", "is_all_day": 0}
    e2 = {"event_id": "a2", "title": "Second", "start_time": "2026-05-27T08:00:00", "end_time": "2026-05-27T10:00:00", "description": "", "location": "", "is_all_day": 0}
    asyncio.get_event_loop().run_until_complete(db.upsert_event(e1))
    asyncio.get_event_loop().run_until_complete(db.upsert_event(e2))
    all_events = asyncio.get_event_loop().run_until_complete(db.get_all_events())
    assert len(all_events) == 2
