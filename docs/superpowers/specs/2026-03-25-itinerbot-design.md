# ItinerBot Design Spec

## Overview

ItinerBot is a Discord bot that connects to a Google Calendar to keep a small friend group informed about their upcoming trip. It sends nightly itinerary summaries for trip days, escalating alerts for ticket purchases, and attempts to auto-lookup ticket sale times when they're missing.

## Core Concepts

**Trip date:** May 26, 2026

The calendar date determines event type:
- **Before May 26** = ticket purchase event
- **On or after May 26** = trip activity

No tagging or prefixes needed.

## Architecture

A single Python process running on the user's PC with three components:

1. **Calendar Sync** — Polls Google Calendar API every 5 minutes, stores events in a local SQLite database.
2. **Alert Scheduler** — Checks the DB for upcoming events and triggers alerts at the right times.
3. **Discord Bot** — Posts messages to a dedicated `#trip-alerts` channel.

All components run in one process using `discord.py` background tasks and APScheduler.

## Event Types & Alert Logic

### Trip Activity Events (May 26+)

- **Nightly itinerary at 9pm** — Bot posts a summary of the next day's activities to the channel. Skips posting if the next day has no events. Stops after `TRIP_END_DATE`.

### Ticket Events (Before May 26)

Escalating alerts:
1. **Night before at 9pm** — Included in the 9pm nightly post alongside any trip itinerary: "Tomorrow: Buy tickets for [Event] at [time]!"
2. **30 minutes before sale time** — "[Event] tickets go live in 30 minutes!"
3. **At sale time** — "TICKETS LIVE NOW for [Event]! Go go go!"

### 9pm Nightly Post

The 9pm post is always a single combined message with two sections (when applicable):
1. **Ticket callouts** — any ticket events happening the next day
2. **Trip itinerary** — activities for the next day (May 26+ only)

Either section is omitted if there's nothing to show. If both sections are empty, no message is sent.

## Sale Time Lookup

When the bot detects a ticket event with no specific time (all-day event):

1. Attempts a web search using the event title + "ticket on sale time" to find the sale time.
2. **If found:** Updates the Google Calendar event with the discovered time. Posts to channel: "Found sale time for [Event]: [time]! Calendar updated."
3. **If not found:** Posts to channel: "Couldn't find a sale time for [Event] — someone look it up and update the calendar!"
4. This check runs when the event is first synced (`lookup_initial`) and again the night before as a fallback (`lookup_nightly`). Two separate attempts tracked independently.
5. If the Google Calendar write fails when updating the sale time, the bot posts the discovered time to the channel so someone can update the calendar manually.

## Data & Storage

**SQLite database** with one table for cached calendar events:

| Column        | Type    | Description                              |
|---------------|---------|------------------------------------------|
| event_id      | TEXT PK | Google Calendar event ID                 |
| title         | TEXT    | Event title                              |
| start_time    | TEXT    | ISO 8601 start time                      |
| end_time      | TEXT    | ISO 8601 end time                        |
| description   | TEXT    | Event description                        |
| location      | TEXT    | Event location                           |
| is_all_day    | INTEGER | 1 if all-day event, 0 otherwise          |
| resolved_time | TEXT    | Discovered sale time (ISO 8601) for all-day ticket events |
| alert_night   | INTEGER | 1 if night-before alert sent             |
| alert_30min   | INTEGER | 1 if 30-min alert sent                   |
| alert_now     | INTEGER | 1 if at-time alert sent                  |
| lookup_initial| INTEGER | 1 if sale time lookup attempted on first sync |
| lookup_nightly| INTEGER | 1 if sale time lookup attempted night-before  |

The calendar is the source of truth. The DB is a local cache for tracking alert state so the bot doesn't spam on restart.

Events deleted from the calendar are removed from the DB on the next sync cycle, cancelling any pending alerts.

APScheduler uses an SQLite job store (not in-memory) so dynamically scheduled alerts survive bot restarts.

## Tech Stack

- **Python 3.10+**
- **discord.py** — Discord integration
- **google-api-python-client + google-auth-oauthlib** — Google Calendar API (read + write for sale time updates)
- **SQLite** (via `sqlite3` stdlib) — Local event cache and alert state
- **APScheduler** — Scheduling nightly itinerary, polling, and timed alerts
- **SerpAPI** (free tier) — Web search to find ticket on-sale times. If the API call fails, falls back to nudging the group in Discord.

## Configuration

`.env` file with:

| Variable              | Description                          |
|-----------------------|--------------------------------------|
| DISCORD_TOKEN         | Discord bot token                    |
| GOOGLE_CREDENTIALS    | Path to Google OAuth credentials     |
| CHANNEL_ID            | Discord channel ID for #trip-alerts  |
| TRIP_START_DATE       | Trip start date (2026-05-26)         |
| TRIP_END_DATE         | Trip end date — nightly itinerary stops after this |
| TIMEZONE              | Timezone for all alerts and date boundary logic (e.g. America/Los_Angeles) |
| SERPAPI_KEY            | SerpAPI key for ticket sale time lookups (free tier) |

## Hosting

Runs locally on the user's PC. The bot process needs to stay running for alerts to fire.

## Project Location

`C:\Users\Jeff\Documents\Github_new\ItinerBot`
