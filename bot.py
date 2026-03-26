# bot.py
import logging
import re
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
intents.message_content = True
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
        events = cal.fetch_events(config.CALENDAR_ID)
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
        # Normalize and parse discovered time
        clean_time = time_str.strip()
        # Remove trailing timezone abbreviations like EST, PST, etc.
        clean_time = re.sub(r"\s+[A-Z]{2,4}$", "", clean_time).strip()
        # Normalize "a.m."/"p.m." to "AM"/"PM"
        clean_time = re.sub(r"a\.m\.", "AM", clean_time, flags=re.IGNORECASE)
        clean_time = re.sub(r"p\.m\.", "PM", clean_time, flags=re.IGNORECASE)
        clean_time = clean_time.strip()
        try:
            # Try formats: "10:00 AM", "10:00AM", "10:00" (24h)
            time_part = None
            for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
                try:
                    time_part = datetime.strptime(clean_time, fmt)
                    break
                except ValueError:
                    continue
            if time_part is None:
                raise ValueError(f"No format matched: {clean_time}")
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
            cal.update_event_time(config.CALENDAR_ID, event["event_id"], resolved_iso, end_iso)
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
# Discord commands
# ---------------------------------------------------------------------------
@bot.command(name="tickets")
async def cmd_tickets(ctx):
    """List all upcoming ticket events and their sale times."""
    all_events = await db.get_all_events()
    ticket_events = [
        e for e in all_events
        if is_ticket_event(e["start_time"], config.TRIP_START_DATE)
    ]
    if not ticket_events:
        await ctx.send("No upcoming ticket events!")
        return

    lines = ["**Upcoming Ticket Events:**"]
    for ev in ticket_events:
        date_str = ev["start_time"][:10]
        if ev.get("resolved_time"):
            time_dt = datetime.fromisoformat(ev["resolved_time"])
            time_display = time_dt.strftime("%#I:%M %p")
            lines.append(f"- {date_str} | **{ev['title']}** | Sale at {time_display}")
        else:
            lines.append(f"- {date_str} | **{ev['title']}** | Sale time unknown")
    await ctx.send("\n".join(lines))


@bot.command(name="settime")
async def cmd_settime(ctx, *, args: str):
    """Set a sale time for a ticket event. Usage: !settime <event name> <time>
    Example: !settime teamLab 10:00 AM"""
    # Parse time from end of args — look for time pattern at the end
    time_match = re.search(r"(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)\s*$", args)
    if not time_match:
        await ctx.send("Couldn't find a time. Usage: `!settime teamLab 10:00 AM`")
        return

    time_str = time_match.group(1).strip()
    search_name = args[:time_match.start()].strip()

    if not search_name:
        await ctx.send("Please include the event name. Usage: `!settime teamLab 10:00 AM`")
        return

    # Find matching ticket event
    all_events = await db.get_all_events()
    ticket_events = [
        e for e in all_events
        if is_ticket_event(e["start_time"], config.TRIP_START_DATE)
    ]

    match = None
    search_lower = search_name.lower()
    for ev in ticket_events:
        if search_lower in ev["title"].lower():
            match = ev
            break

    if not match:
        names = ", ".join(ev["title"] for ev in ticket_events)
        await ctx.send(f"No ticket event matching '{search_name}'. Available: {names}")
        return

    # Parse the time
    clean_time = time_str.strip()
    try:
        time_part = None
        for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
            try:
                time_part = datetime.strptime(clean_time, fmt)
                break
            except ValueError:
                continue
        if time_part is None:
            raise ValueError(f"No format matched: {clean_time}")

        event_date = match["start_time"][:10]
        resolved_iso = f"{event_date}T{time_part.strftime('%H:%M:%S')}"
        parsed = datetime.fromisoformat(resolved_iso)
    except ValueError:
        await ctx.send(f"Couldn't parse time '{time_str}'. Try format like `10:00 AM` or `14:00`")
        return

    # Save to DB
    await db.set_resolved_time(match["event_id"], resolved_iso)

    # Try to update Google Calendar
    try:
        end_iso = (parsed + timedelta(hours=1)).isoformat()
        cal.update_event_time(config.CALENDAR_ID, match["event_id"], resolved_iso, end_iso)
        await ctx.send(
            f"Set sale time for **{match['title']}** to "
            f"{parsed.strftime('%#I:%M %p')} on {event_date}. Calendar updated!"
        )
    except Exception as exc:
        logger.error("Failed to update calendar: %s", exc)
        await ctx.send(
            f"Set sale time for **{match['title']}** to "
            f"{parsed.strftime('%#I:%M %p')} on {event_date}. "
            f"(Couldn't update calendar — but alerts will still work)"
        )

    # Schedule alerts for this event
    updated = await db.get_event(match["event_id"])
    if updated:
        await schedule_ticket_alerts(updated)


@bot.command(name="itinerary")
async def cmd_itinerary(ctx):
    """Show tomorrow's schedule on demand."""
    now = datetime.now(tz)
    tomorrow = now.date() + timedelta(days=1)
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

    message = format_nightly_post(trip_events=trip_events, ticket_events=ticket_events)
    if not message:
        await ctx.send(f"Nothing planned for tomorrow ({tomorrow_str}).")
    else:
        await ctx.send(message)


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
