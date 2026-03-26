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
