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
