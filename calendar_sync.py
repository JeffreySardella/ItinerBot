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
