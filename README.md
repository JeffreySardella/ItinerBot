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
