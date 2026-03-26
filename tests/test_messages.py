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
