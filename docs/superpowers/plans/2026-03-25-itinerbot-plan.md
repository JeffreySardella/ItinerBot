# ItinerBot Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Discord bot that syncs with Google Calendar to send nightly trip itineraries and escalating ticket-sale alerts to a friend group's Discord channel.

**Architecture:** Single Python process with three components — Calendar Sync (polls Google Calendar every 5 min, caches in SQLite), Alert Scheduler (APScheduler with SQLite job store for timed alerts), and Discord Bot (discord.py posting to one channel). Events before the trip start date are ticket purchases; events on/after are trip activities.

**Tech Stack:** Python 3.10+, discord.py, google-api-python-client, google-auth-oauthlib, APScheduler, aiosqlite, SerpAPI (google-search-results), python-dotenv

**Spec:** `docs/superpowers/specs/2026-03-25-itinerbot-design.md`

---

## File Structure

```
ItinerBot/
├── bot.py              # Entry point: Discord bot setup, on_ready, runs everything
├── config.py           # Loads .env, exposes typed config values
├── database.py         # SQLite schema + CRUD for cached events
├── calendar_sync.py    # Google Calendar API polling + DB sync
├── alerts.py           # Alert scheduling logic (APScheduler jobs)
├── messages.py         # Discord message formatting (embeds)
├── sale_lookup.py      # SerpAPI sale-time search + calendar write-back
├── requirements.txt    # Dependencies
├── .env.example        # Template for required env vars
├── tests/
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_calendar_sync.py
│   ├── test_alerts.py
│   ├── test_messages.py
│   └── test_sale_lookup.py
```

---

## Chunk 1: Project Setup + Config + Database

### Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: Create requirements.txt**

```
discord.py>=2.3.0
google-api-python-client>=2.100.0
google-auth-oauthlib>=1.1.0
google-auth-httplib2>=0.2.0
APScheduler>=3.10.0
aiosqlite>=0.19.0
google-search-results>=2.4.0
python-dotenv>=1.0.0
pytz>=2024.1
```

- [ ] **Step 2: Create .env.example**

```
DISCORD_TOKEN=
GOOGLE_CREDENTIALS=credentials.json
CHANNEL_ID=
TRIP_START_DATE=2026-05-26
TRIP_END_DATE=2026-06-01
TIMEZONE=America/Los_Angeles
SERPAPI_KEY=
```

- [ ] **Step 3: Create .gitignore**

```
__pycache__/
*.pyc
.env
token.json
credentials.json
*.db
```

- [ ] **Step 4: Install dependencies**

Run: `cd C:\Users\Jeff\Documents\Github_new\ItinerBot && pip install -r requirements.txt`
Expected: All packages install successfully

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .env.example .gitignore
git commit -m "feat: add project scaffolding"
```

---

### Task 2: Config module

**Files:**
- Create: `config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

```python
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

    # Force reimport to pick up env
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\Jeff\Documents\Github_new\ItinerBot && python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Write implementation**

```python
# config.py
import os
from datetime import date

from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
TRIP_START_DATE = date.fromisoformat(os.environ["TRIP_START_DATE"])
TRIP_END_DATE = date.fromisoformat(os.environ["TRIP_END_DATE"])
TIMEZONE = os.environ.get("TIMEZONE", "America/Los_Angeles")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS", "credentials.json")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")

if TRIP_START_DATE >= TRIP_END_DATE:
    raise ValueError("TRIP_START_DATE must be before TRIP_END_DATE")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Users\Jeff\Documents\Github_new\ItinerBot && python -m pytest tests/test_config.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: add config module with env loading and validation"
```

---

### Task 3: Database module

**Files:**
- Create: `database.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Write failing tests**

```python
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
        "event_id": "e1",
        "title": "Morning Hike",
        "start_time": "2026-05-27T08:00:00",
        "end_time": "2026-05-27T10:00:00",
        "description": "",
        "location": "",
        "is_all_day": 0,
    }
    e2 = {
        "event_id": "e2",
        "title": "Dinner",
        "start_time": "2026-05-27T18:00:00",
        "end_time": "2026-05-27T20:00:00",
        "description": "",
        "location": "",
        "is_all_day": 0,
    }
    e3 = {
        "event_id": "e3",
        "title": "Other day",
        "start_time": "2026-05-28T10:00:00",
        "end_time": "2026-05-28T12:00:00",
        "description": "",
        "location": "",
        "is_all_day": 0,
    }
    asyncio.get_event_loop().run_until_complete(db.upsert_event(e1))
    asyncio.get_event_loop().run_until_complete(db.upsert_event(e2))
    asyncio.get_event_loop().run_until_complete(db.upsert_event(e3))

    events = asyncio.get_event_loop().run_until_complete(
        db.get_events_for_date("2026-05-27")
    )
    assert len(events) == 2
    assert {e["title"] for e in events} == {"Morning Hike", "Dinner"}


def test_update_alert_flag(db):
    event = {
        "event_id": "x1",
        "title": "Test",
        "start_time": "2026-04-10T09:00:00",
        "end_time": "2026-04-10T10:00:00",
        "description": "",
        "location": "",
        "is_all_day": 0,
    }
    asyncio.get_event_loop().run_until_complete(db.upsert_event(event))
    asyncio.get_event_loop().run_until_complete(
        db.set_flag("x1", "alert_night", 1)
    )
    result = asyncio.get_event_loop().run_until_complete(db.get_event("x1"))
    assert result["alert_night"] == 1


def test_set_resolved_time(db):
    event = {
        "event_id": "t1",
        "title": "Buy Concert Tix",
        "start_time": "2026-04-20",
        "end_time": "2026-04-20",
        "description": "",
        "location": "",
        "is_all_day": 1,
    }
    asyncio.get_event_loop().run_until_complete(db.upsert_event(event))
    asyncio.get_event_loop().run_until_complete(
        db.set_resolved_time("t1", "2026-04-20T10:00:00")
    )
    result = asyncio.get_event_loop().run_until_complete(db.get_event("t1"))
    assert result["resolved_time"] == "2026-04-20T10:00:00"


def test_delete_removed_events(db):
    e1 = {
        "event_id": "keep",
        "title": "Keep",
        "start_time": "2026-05-01T10:00:00",
        "end_time": "2026-05-01T12:00:00",
        "description": "",
        "location": "",
        "is_all_day": 0,
    }
    e2 = {
        "event_id": "remove",
        "title": "Remove",
        "start_time": "2026-05-02T10:00:00",
        "end_time": "2026-05-02T12:00:00",
        "description": "",
        "location": "",
        "is_all_day": 0,
    }
    asyncio.get_event_loop().run_until_complete(db.upsert_event(e1))
    asyncio.get_event_loop().run_until_complete(db.upsert_event(e2))
    asyncio.get_event_loop().run_until_complete(
        db.delete_events_not_in(["keep"])
    )
    assert asyncio.get_event_loop().run_until_complete(db.get_event("keep")) is not None
    assert asyncio.get_event_loop().run_until_complete(db.get_event("remove")) is None


def test_get_all_events(db):
    e1 = {
        "event_id": "a1",
        "title": "First",
        "start_time": "2026-04-15T10:00:00",
        "end_time": "2026-04-15T10:30:00",
        "description": "",
        "location": "",
        "is_all_day": 0,
    }
    e2 = {
        "event_id": "a2",
        "title": "Second",
        "start_time": "2026-05-27T08:00:00",
        "end_time": "2026-05-27T10:00:00",
        "description": "",
        "location": "",
        "is_all_day": 0,
    }
    asyncio.get_event_loop().run_until_complete(db.upsert_event(e1))
    asyncio.get_event_loop().run_until_complete(db.upsert_event(e2))
    all_events = asyncio.get_event_loop().run_until_complete(db.get_all_events())
    assert len(all_events) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\Jeff\Documents\Github_new\ItinerBot && python -m pytest tests/test_database.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'database'`

- [ ] **Step 3: Write implementation**

```python
# database.py
import aiosqlite

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    description TEXT DEFAULT '',
    location TEXT DEFAULT '',
    is_all_day INTEGER DEFAULT 0,
    resolved_time TEXT,
    alert_night INTEGER DEFAULT 0,
    alert_30min INTEGER DEFAULT 0,
    alert_now INTEGER DEFAULT 0,
    lookup_initial INTEGER DEFAULT 0,
    lookup_nightly INTEGER DEFAULT 0
)
"""


class Database:
    def __init__(self, db_path: str = "itinerbot.db"):
        self._path = db_path
        self._db = None

    async def init(self):
        self._db = await aiosqlite.connect(self._path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute(CREATE_TABLE)
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()

    async def upsert_event(self, event: dict):
        await self._db.execute(
            """INSERT INTO events (event_id, title, start_time, end_time,
                description, location, is_all_day)
               VALUES (:event_id, :title, :start_time, :end_time,
                :description, :location, :is_all_day)
               ON CONFLICT(event_id) DO UPDATE SET
                title=:title, start_time=:start_time, end_time=:end_time,
                description=:description, location=:location,
                is_all_day=:is_all_day
            """,
            event,
        )
        await self._db.commit()

    async def get_event(self, event_id: str) -> dict | None:
        cursor = await self._db.execute(
            "SELECT * FROM events WHERE event_id = ?", (event_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_events_for_date(self, date_str: str) -> list[dict]:
        cursor = await self._db.execute(
            """SELECT * FROM events
               WHERE start_time LIKE ? || '%'
               ORDER BY start_time""",
            (date_str,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def set_flag(self, event_id: str, flag: str, value: int):
        allowed = {"alert_night", "alert_30min", "alert_now",
                    "lookup_initial", "lookup_nightly"}
        if flag not in allowed:
            raise ValueError(f"Invalid flag: {flag}")
        await self._db.execute(
            f"UPDATE events SET {flag} = ? WHERE event_id = ?",
            (value, event_id),
        )
        await self._db.commit()

    async def set_resolved_time(self, event_id: str, resolved_time: str):
        await self._db.execute(
            "UPDATE events SET resolved_time = ? WHERE event_id = ?",
            (resolved_time, event_id),
        )
        await self._db.commit()

    async def delete_events_not_in(self, keep_ids: list[str]):
        if not keep_ids:
            await self._db.execute("DELETE FROM events")
        else:
            placeholders = ",".join("?" for _ in keep_ids)
            await self._db.execute(
                f"DELETE FROM events WHERE event_id NOT IN ({placeholders})",
                keep_ids,
            )
        await self._db.commit()

    async def get_all_events(self) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM events ORDER BY start_time"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
```

- [ ] **Step 4: Run tests**

Run: `cd C:\Users\Jeff\Documents\Github_new\ItinerBot && python -m pytest tests/test_database.py -v`
Expected: All 6 tests pass

- [ ] **Step 5: Commit**

```bash
git add database.py tests/test_database.py
git commit -m "feat: add database module with event cache and alert tracking"
```

---

## Chunk 2: Google Calendar Sync + Message Formatting

### Task 4: Calendar sync module

**Files:**
- Create: `calendar_sync.py`
- Create: `tests/test_calendar_sync.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\Jeff\Documents\Github_new\ItinerBot && python -m pytest tests/test_calendar_sync.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'calendar_sync'`

- [ ] **Step 3: Write implementation**

```python
# calendar_sync.py
import logging
import os
from datetime import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_PATH = "token.json"


class CalendarSync:
    def __init__(self, credentials_path: str):
        self._credentials_path = credentials_path
        self._service = None

    def authenticate(self):
        """Authenticate with Google Calendar API. Opens browser on first run."""
        creds = None
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        self._service = build("calendar", "v3", credentials=creds)
        logger.info("Google Calendar authenticated.")

    def fetch_events(self, calendar_id: str = "primary") -> list[dict]:
        """Fetch all upcoming events from the calendar."""
        now = datetime.utcnow().isoformat() + "Z"
        results = (
            self._service.events()
            .list(
                calendarId=calendar_id,
                timeMin=now,
                maxResults=250,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        items = results.get("items", [])
        return [self._parse_event(item) for item in items]

    def update_event_time(self, calendar_id: str, event_id: str,
                          start_iso: str, end_iso: str):
        """Update an event's start/end time on Google Calendar."""
        event = self._service.events().get(
            calendarId=calendar_id, eventId=event_id
        ).execute()
        event["start"] = {"dateTime": start_iso}
        event["end"] = {"dateTime": end_iso}
        self._service.events().update(
            calendarId=calendar_id, eventId=event_id, body=event
        ).execute()
        logger.info("Updated event %s time to %s", event_id, start_iso)

    def _parse_event(self, gcal_event: dict) -> dict:
        """Convert a Google Calendar event dict to our DB format."""
        start = gcal_event["start"]
        end = gcal_event["end"]
        is_all_day = "date" in start and "dateTime" not in start

        return {
            "event_id": gcal_event["id"],
            "title": gcal_event.get("summary", "Untitled"),
            "start_time": start.get("date") if is_all_day else start.get("dateTime"),
            "end_time": end.get("date") if is_all_day else end.get("dateTime"),
            "description": gcal_event.get("description", ""),
            "location": gcal_event.get("location", ""),
            "is_all_day": 1 if is_all_day else 0,
        }
```

- [ ] **Step 4: Run tests**

Run: `cd C:\Users\Jeff\Documents\Github_new\ItinerBot && python -m pytest tests/test_calendar_sync.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add calendar_sync.py tests/test_calendar_sync.py
git commit -m "feat: add calendar sync with Google Calendar API integration"
```

---

### Task 5: Message formatting module

**Files:**
- Create: `messages.py`
- Create: `tests/test_messages.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_messages.py
from messages import format_nightly_post, format_ticket_30min, format_ticket_live


def test_nightly_post_trip_only():
    trip_events = [
        {"title": "Morning Hike", "start_time": "2026-05-27T08:00:00", "location": "Trail"},
        {"title": "Dinner", "start_time": "2026-05-27T18:00:00", "location": "Restaurant"},
    ]
    result = format_nightly_post(trip_events=trip_events, ticket_events=[])
    assert "Morning Hike" in result
    assert "Dinner" in result
    assert "8:00 AM" in result


def test_nightly_post_tickets_only():
    ticket_events = [
        {"title": "Concert Tix", "start_time": "2026-04-15T10:00:00",
         "resolved_time": "2026-04-15T10:00:00", "is_all_day": 0},
    ]
    result = format_nightly_post(trip_events=[], ticket_events=ticket_events)
    assert "Concert Tix" in result
    assert "10:00 AM" in result


def test_nightly_post_ticket_unknown_time():
    ticket_events = [
        {"title": "Show Tix", "start_time": "2026-04-16",
         "resolved_time": None, "is_all_day": 1},
    ]
    result = format_nightly_post(trip_events=[], ticket_events=ticket_events)
    assert "Show Tix" in result
    assert "unknown" in result.lower()


def test_nightly_post_empty():
    result = format_nightly_post(trip_events=[], ticket_events=[])
    assert result is None


def test_nightly_post_combined():
    trip = [{"title": "Beach", "start_time": "2026-05-27T10:00:00", "location": ""}]
    tickets = [
        {"title": "Tix", "start_time": "2026-04-15T09:00:00",
         "resolved_time": "2026-04-15T09:00:00", "is_all_day": 0}
    ]
    result = format_nightly_post(trip_events=trip, ticket_events=tickets)
    assert "Beach" in result
    assert "Tix" in result


def test_ticket_30min():
    result = format_ticket_30min("Concert Presale")
    assert "30 minutes" in result
    assert "Concert Presale" in result


def test_ticket_live():
    result = format_ticket_live("Concert Presale")
    assert "LIVE NOW" in result
    assert "Concert Presale" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\Jeff\Documents\Github_new\ItinerBot && python -m pytest tests/test_messages.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'messages'`

- [ ] **Step 3: Write implementation**

```python
# messages.py
from datetime import datetime


def _format_time(iso_str: str) -> str:
    """Format ISO time string to human-readable like '8:00 AM'."""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%#I:%M %p")
    except (ValueError, TypeError):
        return iso_str


def _get_ticket_time_display(event: dict) -> str | None:
    """Get display time for a ticket event, using resolved_time if available."""
    if event.get("resolved_time"):
        return _format_time(event["resolved_time"])
    if not event.get("is_all_day") and event.get("start_time") and "T" in event["start_time"]:
        return _format_time(event["start_time"])
    return None


def format_nightly_post(
    trip_events: list[dict], ticket_events: list[dict]
) -> str | None:
    """Format the 9pm nightly post. Returns None if nothing to show."""
    sections = []

    if ticket_events:
        lines = ["**Tickets to Buy Tomorrow:**"]
        for ev in ticket_events:
            time_str = _get_ticket_time_display(ev)
            if time_str:
                lines.append(f"- **{ev['title']}** at {time_str}")
            else:
                lines.append(
                    f"- **{ev['title']}** — sale time unknown, check the calendar!"
                )
        sections.append("\n".join(lines))

    if trip_events:
        lines = ["**Tomorrow's Itinerary:**"]
        for ev in trip_events:
            time_str = _format_time(ev["start_time"])
            loc = f" @ {ev['location']}" if ev.get("location") else ""
            lines.append(f"- {time_str} — **{ev['title']}**{loc}")
        sections.append("\n".join(lines))

    if not sections:
        return None

    return "\n\n".join(sections)


def format_ticket_30min(title: str) -> str:
    return f"**{title}** tickets go live in 30 minutes! Get ready!"


def format_ticket_live(title: str) -> str:
    return f"TICKETS LIVE NOW for **{title}**! Go go go!"
```

- [ ] **Step 4: Run tests**

Run: `cd C:\Users\Jeff\Documents\Github_new\ItinerBot && python -m pytest tests/test_messages.py -v`
Expected: 7 passed

Note: `%#I` is the Windows strftime directive for no-leading-zero hour. On Linux/macOS it would be `%-I`.

- [ ] **Step 5: Commit**

```bash
git add messages.py tests/test_messages.py
git commit -m "feat: add message formatting for nightly posts and ticket alerts"
```

---

## Chunk 3: Sale Time Lookup + Alert Scheduling

### Task 6: Sale time lookup module

**Files:**
- Create: `sale_lookup.py`
- Create: `tests/test_sale_lookup.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_sale_lookup.py
import pytest
from unittest.mock import patch, MagicMock
from sale_lookup import search_sale_time


def test_search_finds_time():
    mock_result = {
        "organic_results": [
            {"snippet": "Tickets go on sale at 10:00 AM EST on April 15, 2026"}
        ]
    }
    with patch("sale_lookup.GoogleSearch") as MockSearch:
        instance = MockSearch.return_value
        instance.get_dict.return_value = mock_result
        result = search_sale_time("Concert Presale", "serpkey123")
    assert result is not None
    assert "10" in result


def test_search_no_results():
    mock_result = {"organic_results": []}
    with patch("sale_lookup.GoogleSearch") as MockSearch:
        instance = MockSearch.return_value
        instance.get_dict.return_value = mock_result
        result = search_sale_time("Obscure Event", "serpkey123")
    assert result is None


def test_search_api_failure():
    with patch("sale_lookup.GoogleSearch") as MockSearch:
        instance = MockSearch.return_value
        instance.get_dict.side_effect = Exception("API error")
        result = search_sale_time("Concert", "serpkey123")
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\Jeff\Documents\Github_new\ItinerBot && python -m pytest tests/test_sale_lookup.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sale_lookup'`

- [ ] **Step 3: Write implementation**

```python
# sale_lookup.py
import logging
import re

from serpapi import GoogleSearch

logger = logging.getLogger(__name__)

TIME_PATTERN = re.compile(
    r"(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm|a\.m\.|p\.m\.)?\s*(?:[A-Z]{2,4})?)"
)


def search_sale_time(event_title: str, api_key: str) -> str | None:
    """Search for a ticket sale time using SerpAPI.

    Returns a time string like '10:00 AM' if found, None otherwise.
    """
    if not api_key:
        logger.warning("No SERPAPI_KEY set, skipping sale time lookup.")
        return None

    query = f"{event_title} ticket on sale time"
    try:
        search = GoogleSearch({"q": query, "api_key": api_key, "num": 5})
        results = search.get_dict()
    except Exception as exc:
        logger.error("SerpAPI search failed for '%s': %s", event_title, exc)
        return None

    snippets = []
    for r in results.get("organic_results", []):
        if r.get("snippet"):
            snippets.append(r["snippet"])

    for snippet in snippets:
        match = TIME_PATTERN.search(snippet)
        if match:
            found = match.group(1).strip()
            logger.info("Found sale time for '%s': %s", event_title, found)
            return found

    logger.info("No sale time found for '%s'", event_title)
    return None
```

- [ ] **Step 4: Run tests**

Run: `cd C:\Users\Jeff\Documents\Github_new\ItinerBot && python -m pytest tests/test_sale_lookup.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add sale_lookup.py tests/test_sale_lookup.py
git commit -m "feat: add SerpAPI sale time lookup with regex extraction"
```

---

### Task 7: Alert scheduling module

**Files:**
- Create: `alerts.py`
- Create: `tests/test_alerts.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\Jeff\Documents\Github_new\ItinerBot && python -m pytest tests/test_alerts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'alerts'`

- [ ] **Step 3: Write implementation**

```python
# alerts.py
import logging
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)


def is_ticket_event(start_time: str, trip_start: date) -> bool:
    """Return True if this event is before the trip (ticket purchase)."""
    date_str = start_time[:10]  # works for both 'YYYY-MM-DD' and 'YYYY-MM-DDTHH:...'
    event_date = date.fromisoformat(date_str)
    return event_date < trip_start


def get_alert_time(event: dict) -> datetime | None:
    """Get the datetime to schedule timed alerts for.

    Returns resolved_time if set, otherwise start_time if timed.
    Returns None for all-day events with no resolved time.
    """
    if event.get("resolved_time"):
        return datetime.fromisoformat(event["resolved_time"])
    if not event.get("is_all_day") and event.get("start_time") and "T" in event["start_time"]:
        return datetime.fromisoformat(event["start_time"])
    return None


def should_send_nightly(today: date, trip_end: date) -> bool:
    """Return True if the nightly post should fire tonight."""
    return today <= trip_end
```

- [ ] **Step 4: Run tests**

Run: `cd C:\Users\Jeff\Documents\Github_new\ItinerBot && python -m pytest tests/test_alerts.py -v`
Expected: All 8 tests pass

- [ ] **Step 5: Commit**

```bash
git add alerts.py tests/test_alerts.py
git commit -m "feat: add alert scheduling helpers"
```

---

## Chunk 4: Bot Integration (Main Entry Point)

### Task 8: Bot entry point — wiring everything together

**Files:**
- Create: `bot.py`

- [ ] **Step 1: Write bot.py**

```python
# bot.py
import logging
import asyncio
from datetime import datetime, date, timedelta

import discord
from discord.ext import commands, tasks
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

import config
from database import Database
from calendar_sync import CalendarSync
from alerts import is_ticket_event, get_alert_time, should_send_nightly
from messages import format_nightly_post, format_ticket_30min, format_ticket_live
from sale_lookup import search_sale_time

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
db = Database()
cal = CalendarSync(config.GOOGLE_CREDENTIALS)
tz = pytz.timezone(config.TIMEZONE)

scheduler = AsyncIOScheduler(
    jobstores={"default": SQLAlchemyJobStore(url="sqlite:///jobs.db")},
    timezone=tz,
)


def get_channel():
    return bot.get_channel(config.CHANNEL_ID)


# ---------------------------------------------------------------------------
# Calendar sync (every 5 minutes)
# ---------------------------------------------------------------------------
@tasks.loop(minutes=5)
async def sync_calendar():
    logger.info("Syncing calendar...")
    try:
        events = cal.fetch_events()
    except Exception as exc:
        logger.error("Calendar fetch failed: %s", exc)
        return

    current_ids = [e["event_id"] for e in events]
    await db.delete_events_not_in(current_ids)

    for event in events:
        existing = await db.get_event(event["event_id"])
        await db.upsert_event(event)

        if existing is None and is_ticket_event(event["start_time"], config.TRIP_START_DATE):
            if event["is_all_day"]:
                await do_sale_lookup(event, "initial")
            await schedule_ticket_alerts(event)

    logger.info("Synced %d events.", len(events))


@sync_calendar.before_loop
async def before_sync():
    await bot.wait_until_ready()


# ---------------------------------------------------------------------------
# Sale time lookup
# ---------------------------------------------------------------------------
async def do_sale_lookup(event: dict, attempt: str):
    """Attempt to find the sale time for an all-day ticket event."""
    flag = f"lookup_{attempt}"
    existing = await db.get_event(event["event_id"])
    if existing and existing.get(flag):
        return

    channel = get_channel()
    time_str = search_sale_time(event["title"], config.SERPAPI_KEY)

    if time_str:
        # Parse the discovered time (e.g. "10:00 AM", "10:00 AM EST")
        event_date = event["start_time"][:10]
        # Strip timezone abbreviations and parse AM/PM
        clean_time = time_str.strip()
        # Remove trailing timezone abbreviations like EST, PST, etc.
        import re
        clean_time = re.sub(r"\s+[A-Z]{2,4}$", "", clean_time).strip()
        try:
            from datetime import datetime as dt_parse
            time_part = dt_parse.strptime(clean_time, "%I:%M %p")
            resolved_iso = f"{event_date}T{time_part.strftime('%H:%M:%S')}"
            parsed = datetime.fromisoformat(resolved_iso)
        except ValueError:
            logger.warning("Could not parse discovered time '%s' for '%s'",
                           time_str, event["title"])
            if channel:
                await channel.send(
                    f"Found a possible sale time for **{event['title']}**: {time_str}, "
                    f"but couldn't parse it. Someone check the calendar!"
                )
            await db.set_flag(event["event_id"], flag, 1)
            return

        await db.set_resolved_time(event["event_id"], resolved_iso)
        await db.set_flag(event["event_id"], flag, 1)

        # Try to update Google Calendar
        try:
            end_iso = (parsed + timedelta(hours=1)).isoformat()
            cal.update_event_time("primary", event["event_id"], resolved_iso, end_iso)
            if channel:
                await channel.send(
                    f"Found sale time for **{event['title']}**: "
                    f"{parsed.strftime('%I:%M %p')}! Calendar updated."
                )
        except Exception as exc:
            logger.error("Failed to update calendar for %s: %s", event["event_id"], exc)
            if channel:
                await channel.send(
                    f"Found sale time for **{event['title']}**: "
                    f"{parsed.strftime('%I:%M %p')}! "
                    f"Couldn't update the calendar — someone do it manually."
                )

        # Schedule timed alerts now that we have a time
        updated_event = await db.get_event(event["event_id"])
        if updated_event:
            await schedule_ticket_alerts(updated_event)
    else:
        await db.set_flag(event["event_id"], flag, 1)
        if channel:
            await channel.send(
                f"Couldn't find a sale time for **{event['title']}** — "
                f"someone look it up and update the calendar!"
            )


# ---------------------------------------------------------------------------
# Alert scheduling
# ---------------------------------------------------------------------------
async def schedule_ticket_alerts(event: dict):
    """Schedule 30-min and at-time alerts for a ticket event."""
    alert_dt = get_alert_time(event)
    if alert_dt is None:
        return

    event_id = event["event_id"]
    title = event["title"]

    now = datetime.now(tz)

    # Ensure alert_dt is timezone-aware
    if alert_dt.tzinfo is None:
        alert_dt = tz.localize(alert_dt)

    # 30-min alert
    thirty_before = alert_dt - timedelta(minutes=30)
    if thirty_before > now:
        scheduler.add_job(
            send_ticket_alert,
            "date",
            run_date=thirty_before,
            args=[event_id, "30min"],
            id=f"{event_id}_30min",
            replace_existing=True,
        )

    # At-time alert
    if alert_dt > now:
        scheduler.add_job(
            send_ticket_alert,
            "date",
            run_date=alert_dt,
            args=[event_id, "now"],
            id=f"{event_id}_now",
            replace_existing=True,
        )


async def send_ticket_alert(event_id: str, alert_type: str):
    """Fire a ticket alert to the channel."""
    event = await db.get_event(event_id)
    if not event:
        return

    flag = f"alert_{alert_type}"
    if event.get(flag):
        return

    channel = get_channel()
    if not channel:
        return

    if alert_type == "30min":
        msg = format_ticket_30min(event["title"])
    else:
        msg = format_ticket_live(event["title"])

    await channel.send(msg)
    await db.set_flag(event_id, flag, 1)


# ---------------------------------------------------------------------------
# Nightly 9pm post
# ---------------------------------------------------------------------------
async def nightly_post():
    """Send the combined 9pm nightly post."""
    now = datetime.now(tz)
    today = now.date()

    if not should_send_nightly(today, config.TRIP_END_DATE):
        return

    tomorrow = today + timedelta(days=1)
    tomorrow_str = tomorrow.isoformat()

    all_events = await db.get_events_for_date(tomorrow_str)

    trip_events = [
        e for e in all_events
        if not is_ticket_event(e["start_time"], config.TRIP_START_DATE)
    ]
    ticket_events = [
        e for e in all_events
        if is_ticket_event(e["start_time"], config.TRIP_START_DATE)
    ]

    # Also do nightly sale lookups for all-day ticket events tomorrow
    for ev in ticket_events:
        if ev.get("is_all_day") and not ev.get("lookup_nightly"):
            await do_sale_lookup(ev, "nightly")
            # Re-fetch to get updated resolved_time
            refreshed = await db.get_event(ev["event_id"])
            if refreshed:
                idx = ticket_events.index(ev)
                ticket_events[idx] = refreshed

    message = format_nightly_post(trip_events=trip_events, ticket_events=ticket_events)
    if not message:
        return

    channel = get_channel()
    if not channel:
        return

    await channel.send(message)

    # Mark night alerts as sent only after successful send
    for ev in ticket_events:
        await db.set_flag(ev["event_id"], "alert_night", 1)


# ---------------------------------------------------------------------------
# Bot events
# ---------------------------------------------------------------------------
@bot.event
async def on_ready():
    await db.init()
    cal.authenticate()

    # Schedule nightly post at 9pm
    scheduler.add_job(
        nightly_post,
        "cron",
        hour=21,
        minute=0,
        id="nightly_post",
        replace_existing=True,
    )
    scheduler.start()

    sync_calendar.start()
    logger.info("ItinerBot online as %s", bot.user)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
bot.run(config.DISCORD_TOKEN)
```

- [ ] **Step 2: Verify bot starts (manual test)**

Create a `.env` file from `.env.example` with real credentials, then:

Run: `cd C:\Users\Jeff\Documents\Github_new\ItinerBot && python bot.py`
Expected: "ItinerBot online as ItinerBot#XXXX" in console. Bot appears online in Discord.

Press Ctrl+C to stop.

- [ ] **Step 3: Verify calendar sync (manual test)**

After starting the bot, check logs for: "Synced X events."
Add a test event to your Google Calendar and wait 5 minutes. Check logs for it appearing.

- [ ] **Step 4: Commit**

```bash
git add bot.py
git commit -m "feat: add bot entry point wiring all components together"
```

---

### Task 9: Create empty `tests/__init__.py` and run full test suite

**Files:**
- Create: `tests/__init__.py`

- [ ] **Step 1: Create tests init**

Create an empty `tests/__init__.py` file.

- [ ] **Step 2: Run full test suite**

Run: `cd C:\Users\Jeff\Documents\Github_new\ItinerBot && python -m pytest tests/ -v`
Expected: All tests pass (20+ tests across all modules)

- [ ] **Step 3: Commit**

```bash
git add tests/__init__.py
git commit -m "chore: add tests init and verify full test suite"
```

---

## Chunk 5: Setup Guide

### Task 10: Google Cloud + Discord setup instructions

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write setup guide in README**

Update `README.md` with:

```markdown
# ItinerBot

Discord bot that syncs with Google Calendar to send trip itineraries and ticket-sale alerts.

## Setup

### 1. Discord Bot

1. Go to https://discord.com/developers/applications
2. Click "New Application" → name it "ItinerBot"
3. Go to Bot tab → click "Reset Token" → copy the token
4. Under Privileged Gateway Intents, enable nothing extra (defaults are fine)
5. Go to OAuth2 → URL Generator:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `View Channels`
6. Copy the generated URL → open in browser → add to your server
7. Create a `#trip-alerts` channel and copy its ID (right-click → Copy Channel ID, enable Developer Mode in Discord settings if needed)

### 2. Google Calendar API

1. Go to https://console.cloud.google.com/
2. Create a new project (or use existing)
3. Enable the Google Calendar API
4. Go to Credentials → Create Credentials → OAuth Client ID
   - Application type: Desktop app
   - Download the JSON → save as `credentials.json` in the ItinerBot folder
5. On first run, the bot will open a browser window to authenticate with your Google account

### 3. SerpAPI (optional, for auto sale-time lookup)

1. Go to https://serpapi.com/ → sign up (free tier: 100 searches/month)
2. Copy your API key

### 4. Configure

1. Copy `.env.example` to `.env`
2. Fill in all values:
   - `DISCORD_TOKEN` — from step 1
   - `CHANNEL_ID` — from step 1
   - `GOOGLE_CREDENTIALS` — path to `credentials.json`
   - `TRIP_START_DATE` — your trip start date (YYYY-MM-DD)
   - `TRIP_END_DATE` — your trip end date (YYYY-MM-DD)
   - `TIMEZONE` — your timezone (e.g. `America/Los_Angeles`)
   - `SERPAPI_KEY` — from step 3 (leave blank to skip auto-lookup)

### 5. Install & Run

```bash
pip install -r requirements.txt
python bot.py
```

The bot must stay running for alerts to work. On first run it will open a browser to authenticate with Google.

## How It Works

- **Events before your trip date** = ticket purchase alerts (escalating: night before → 30 min → LIVE NOW)
- **Events on/after your trip date** = trip activities (nightly itinerary at 9pm)
- **All-day events before trip** = bot tries to find the sale time automatically via web search
- Just add events to your Google Calendar — the bot handles the rest
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add setup guide for Discord, Google Calendar, and SerpAPI"
```
