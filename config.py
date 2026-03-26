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
CALENDAR_ID = os.environ.get("CALENDAR_ID", "primary")

if TRIP_START_DATE >= TRIP_END_DATE:
    raise ValueError("TRIP_START_DATE must be before TRIP_END_DATE")
