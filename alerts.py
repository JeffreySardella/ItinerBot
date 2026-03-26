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
