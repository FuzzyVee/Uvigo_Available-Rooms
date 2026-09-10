#!/usr/bin/env python3
"""
ESEI (UVigo) room availability scraper
======================================
Downloads the PUBLIC Google Calendar feeds that power the ESEI timetable
pages and converts them into data.json, consumed by index.html.

No API key is needed: this uses the public ".ics" feed of each calendar,
the same one Google Calendar itself uses for the embedded view.

Usage:
    pip install recurring-ical-events
    python scraper.py

Run it by hand, or let the included GitHub Action run it automatically
every 6 hours (see .github/workflows/update.yml).
"""

import datetime as dt
import json
import re
import sys
import urllib.request

from icalendar import Calendar                       # installed automatically
import recurring_ical_events                         #   with recurring-ical-events

# ----------------------------------------------------------------------------
# 1. CONFIGURATION
# ----------------------------------------------------------------------------
# Public Google Calendar IDs. Each ESEI year page embeds one or more of these.
# They were extracted from the <iframe> on the timetable pages. To add another
# year, open that year's page, copy the iframe src from DevTools and add every
# src=... value you find here.
CALENDARS = [
    "esei.uvigo.es_gq96dj81nddqrptf1ohm38lvtg@group.calendar.google.com",
    "esei.uvigo.es_32m4nabv1hc97h01m5l9l7pl90@group.calendar.google.com",
    "esei.uvigo.es_111965ep6irul3pfiupmol5si0@group.calendar.google.com",
    "esei.uvigo.es_ebcdriqohr05h8k6slere2n8og@group.calendar.google.com",
    "esei.uvigo.es_g7mffdi109voacmlift21cno1s@group.calendar.google.com",
    "esei.uvigo.es_vkgffkl4tqf0pute7ske69m450@group.calendar.google.com",
    "esei.uvigo.es_h3bdlmtfparmo738892ds78cu4@group.calendar.google.com",
    "esei.uvigo.es_fvhcpcc4is27trfrkoshfrhkjk@group.calendar.google.com",
    "esei.uvigo.es_q0sjjh13if6nflfvtevhia06a8@group.calendar.google.com",
    "esei.uvigo.es_571iaa6jp3qqied2u8hdi808k8@group.calendar.google.com",
]

FEED_URL = "https://calendar.google.com/calendar/ical/{cid}/public/basic.ics"

# How many days of recurring events to expand around today.
DAYS_BEHIND = 7
DAYS_AHEAD  = 100

# Event titles look like "BDII_3 [SO1]" -> room between square brackets.
ROOM_RE = re.compile(r"\[([^\]]+)\]")

# ----------------------------------------------------------------------------
# 2. HELPERS
# ----------------------------------------------------------------------------
def fetch_ics(calendar_id: str) -> bytes:
    url = FEED_URL.format(cid=calendar_id)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except Exception as exc:                       # keep going if one calendar fails
        print(f"  ! could not fetch {calendar_id}: {exc}", file=sys.stderr)
        return b""


def room_and_subject(summary: str, location: str):
    """Return (room, subject). The room is taken from the Google Calendar
    'Location' field if present, otherwise from the [ROOM] part of the title."""
    room = location.strip() if location else None
    m = ROOM_RE.search(summary)
    if not room and m:
        room = m.group(1).strip()
    subject = ROOM_RE.sub("", summary).strip()
    return room, subject


def as_date(value):
    """icalendar returns datetime or date depending on the event type."""
    if isinstance(value, dt.datetime):
        return value.date(), value.strftime("%H:%M")
    return value, None

# ----------------------------------------------------------------------------
# 3. MAIN
# ----------------------------------------------------------------------------
def main():
    today = dt.date.today()
    start = today - dt.timedelta(days=DAYS_BEHIND)
    end   = today + dt.timedelta(days=DAYS_AHEAD)
    print(f"Expanding events between {start} and {end} ...")

    out, no_room = [], 0
    for cid in CALENDARS:
        raw = fetch_ics(cid)
        if not raw:
            continue
        cal = Calendar.from_ical(raw)
        for ev in recurring_ical_events.of(cal).between(start, end):
            summary  = str(ev.get("SUMMARY", "")).strip()
            location = str(ev.get("LOCATION", "") or "").strip()
            if not summary:
                continue
            d1, t1 = as_date(ev.decoded("DTSTART"))
            d2, t2 = as_date(ev.decoded("DTEND"))
            room, subject = room_and_subject(summary, location)
            if not room:
                no_room += 1
            out.append({
                "subject": subject,
                "room":    room,
                "date":    d1.isoformat(),
                "start":   t1 or "00:00",
                "end":     t2 or "23:59",
                "raw":     summary,
            })
        print(f"  ok {cid}")

    out.sort(key=lambda e: (e["date"], e["start"], e["room"] or ""))
    data = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "timezone": "Europe/Madrid",
        "calendar_count": len(CALENDARS),
        "event_count": len(out),
        "events": out,
    }
    with open("data.json", "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    print(f"Wrote data.json with {len(out)} events "
          f"({no_room} had no room info).")


if __name__ == "__main__":
    main()
