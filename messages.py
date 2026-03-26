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
