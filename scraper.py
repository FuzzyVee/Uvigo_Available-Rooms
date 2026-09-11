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
import base64

from icalendar import Calendar                       
import recurring_ical_events                        

# ----------------------------------------------------------------------------
# 1. CONFIGURATION
# ----------------------------------------------------------------------------
# Public Google Calendar IDs, grouped by the page they came from.
# How to add a group: open that year's timetable page, press F12 -> Elements,
# search for "iframe", right-click the <iframe> tag and copy its outerHTML,
# then copy every src=... calendar ID you see into a new entry below.
CALENDAR_GROUPS = {
    "Grado 1 - 1C": [
        "esei.uvigo.es_aqrano1tgp25mr9n2lh1mlbr24@group.calendar.google.com",
        "esei.uvigo.es_1pmsf23urm8mt0n6jmau7tt960@group.calendar.google.com",
        "esei.uvigo.es_f2fjvmvve47snqgdo8juqi1jf8@group.calendar.google.com",
        "esei.uvigo.es_mi24008rkn5210hi3jr8sc7ok0@group.calendar.google.com",
        "esei.uvigo.es_gspvq926nhqj8pllpgtkh4j7ko@group.calendar.google.com",
        "esei.uvigo.es_ng93okvrg45u8o1cjat3fv9i6k@group.calendar.google.com",
        "esei.uvigo.es_3l5uuk4p1gb7pkni9ahl9qm4tc@group.calendar.google.com",
        "esei.uvigo.es_ul3lof7g790sv89ddn5a9st7uc@group.calendar.google.com",
        "esei.uvigo.es_62a1j9sq3qqfg6bktbguoujnms@group.calendar.google.com",
        "esei.uvigo.es_pnc49is9fmnuuk9rnh26quqgp4@group.calendar.google.com",
    ],
    "Grado 2 - 1C": [
        "esei.uvigo.es_s4p1mjtsce25duscpviupm2j7o@group.calendar.google.com",
        "esei.uvigo.es_oa5hsjq30s1pbma0btefe79t7c@group.calendar.google.com",
        "esei.uvigo.es_asfl1qp1481839v5rp5snigh6s@group.calendar.google.com",
        "esei.uvigo.es_lgjn9pipm8e5prahq5qqdlk1d0@group.calendar.google.com",
        "esei.uvigo.es_obiu0ipfihsvj7eqlo8kb4r9mc@group.calendar.google.com",
        "esei.uvigo.es_gspvq926nhqj8pllpgtkh4j7ko@group.calendar.google.com",
        "esei.uvigo.es_2a70p78r038t286bhlpchjjaco@group.calendar.google.com",
        "esei.uvigo.es_m3nk7ba3ag505umm6mumaqju98@group.calendar.google.com",
        "esei.uvigo.es_f0c165gskhdl4e0qbbnag9u7os@group.calendar.google.com",
        "esei.uvigo.es_uvj5jaei3vmcu6fdbde35hgbvs@group.calendar.google.com",
        "esei.uvigo.es_2u12ff9s23tmkm2ksfim273bvs@group.calendar.google.com",
    ],
    "Grado 3 - 1C": [
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
    ],
    "Grado 4 - 1C": [
        "ZXNlaS51dmlnby5lc19ucXJmM2M0bnJpcmk1cTJvN2NxajlwcTFuMEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc190ZDUwbGI5NTA5ODJibHNjbTlqYnE0bjRoa0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc19xdHUzamVuMDdvcmJhczdhYThwMWZtMzlmb0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc19wMnA1NG5wcTVhM2s5ZDZtMGk5MzIwNzhyZ0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc190amZhYXFxNzcwMmdvaDlsMGxpbnY5b3JqZ0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc19ncjhrbXE5bTdubmI2MGdiOWkyOWhrMGxha0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc19xaG1uMzIwNnFwcmRkNzcxcHRscDU0ZHRrOEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc19laTc4dm9jNnFmdGVicHQ3OWZvcTEwNmExb0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc19lbzRwYzgwc3I5bm85c2N1NGI3bW8wc25xOEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc19xa3JyYm81ZTlkNzlhMjBxNmtkc2dvbHRnY0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc18yNnVwYzYyc2hpc29qZDJ1MjNzcGFtMGJ1NEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc191NGZwYXExZmg3MnRhaGxkdjVwOWMxOW1ha0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc18yMWk3MW1uazM5djBnYzMzbzF2aW5yMXF2a0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc19oYWJ0Mm1nN29jNGE2aWVidTczaGpoaWlsb0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc184Y21jdDNhc3YzNmJlZHYwcWJ1bDVxdTc2NEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc19qOWg1bzc1c2szZ2hiMTBlNW44c2t0cG9mZ0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "c_1e7fd190617c56f14e6821faa3fd1d8ad417467dcf2b91bc42ee16aaa4f0d1cb@group.calendar.google.com",
    ],
    "Grado 1IA - 1C": [
        "Y19kMGZyZjAycjgxNm1wcWFsYWV0Ym9mN3ExOEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "Y19wdTN0NWNwa2VsNzJsMjFmcnZmb2pxcTJsMEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "Y18wdHJrdWtpdGw2ZG9lN2RwbzVxMnBrNnR2a0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "Y19yYXFqOGw2bG4xamxzb2I1dHIwcXNjaTU4Y0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "Y180c2llcG1qOWI1Z2w4b204bzVmZWVpNGFhNEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc19nc3B2cTkyNm5ocWo4cGxscGd0a2g0ajdrb0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
    ],
    "Grado 2IA - 1C": [
        "Y19mYzAzZTUzNjdmNjAwZDZlYTgyMjUwZDdjYTYzMGZmNmZjNzUwZDI1NGJkMTJiOWMxOGY1NzZhMjc0NGU1OGFjQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y19iNTY3NTIwY2FhMDc4OWNiOTNiYjM1ZTAzYTY2NWNkZWQ1ZDM1ZjJhZTRkMGVkYjk0NGVhZmVkZDkwZDQ1MzRhQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y19kN2IxYzg4NmE2YzU2YWI2YmE3MjI4YTc3NjAwNGU4MDE0NWVlYTkzZjc2Yzc2NDQ0ZDVhMzVjZjZkZjg2NDBmQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y183ZTI3OGY5Mzk2ZjA0MTRhNTZjMzk0M2Y4ZjIyM2JmMzk3MTAxMzA4NzE4OTkxZDJkMTQ0MDE0YzRkMTRlYzBmQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y183MzA0ZDE3ZDU1Y2Y2ZWY4Zjg4ZjhlNDEyYmM4MTRhMDczM2JlODYyNDlhZmRmMDA5OTBkMmRhODM3MmZlMzY3QGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
    ],
    "Grado 3IA - 1C": [
        "Y181ZDI0NDJlMGRjYzNjZjZjM2MzNDUyNzhmMmNlZDRhNWJkODBjYjEyNGUzZWYxNzI5NDE5MzE0YTZlZDA2OWU0QGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y19mMWQyYTk4NTdmYTBiMTliOTdlNmVhZWVjYzE1ZjA1MTUxNzEzZDhmNGZiZWIwMGQ1ZTg2YTAyYTA0MGE1N2Q0QGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y19iNTk2Y2NjMmQ3ZmQ3ZDFjMTBhNTM1N2Y5MTcxYWMzYWFlMTQ0MTMzYjY1YWI1MGRiNzUwOGVmZDAzNjNiNTMxQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y19mZGJkNjE1ZTRmYjcxODc2NmZhODAzNWQ3NGQ5Nzg5OWI0ZWUxNTZmZjY3YTM1MjgzNzRhMTkwZGIwODA5NDczQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y19mYjMwMjU4MjFjYTEyNGM5NjgwOTViMDVjNDcwYWI4NTRmYmUyZDA2YzA3OTRjZTZmYWQ2YjkwNjA0NjAyOTlmQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
    ],
    "Grado 4IA - 1C": [
        "Y19jZGEwNGE0OGVjZWRmNzM4NjFhOWNjMDhiMTU1NGM4MjhkZDJiZjZjODZiZmIxMTVlMjJhMTFlYTk2MmZlMGMzQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y18zZGZlZGQ2MDdhYTRkODM2ZDJlNThlYTQ4OWI0Mzk1YzVjMDllNmZiNTE0NjNkZTNiNGFiNTMwYTkyMjZmZWMwQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y19lNWJkZmY3ODgyMGJmZjgzMTk4MzFlYmYxZjFmMzI3M2IyZDhkMmQxNjYwMjFkYzdmNmUyOTY4NTQyNTQ5ZjQ4QGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y19jZTNiOTQ3ODIxNjY3ZjA4MDY5NWRhNmJkY2IwNWNkZjgzMzZjZTFlZjY3ZjkyMzE2NDBmMjAzNTZkZDA2YjMwQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y181OTc1NDgzMDAxOGEwMzkwZmMyMTRkMTdjNWY5NTE5M2RjMmIwMTRkYzhmYmY0OWYwYmVlOGQ0NzUzN2NkYmY4QGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y19jM2MxMzdjMjBiNTJlN2NmMWFmOWQxOTEzZjE0YTRlN2FhN2RmOGMyZDQwZjNjN2ZmNTIyMDdlMjU0NmJmYmEwQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y182NDNjMDBhNjE3M2RkMTE0OWRlNmY3YTQ0NDJiYzVhNjYyYzdhMTY0ZjExYjdiNTM0MzljNDMxZmE1NjNiNGViQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
    ],
    # --- add more groups here, e.g.: ---------------------------
    # "Grao 1 - 1C": [ ...paste calendar IDs from that page... ],
    # "Grao 2 - 1C": [ ... ],
    # "Grao 4 - 1C": [ ... ],
    # "Grao 1 - 2C": [ ... ],   # 2nd semester (Feb-Jun)
    # "Master 1 - 1C": [ ... ],
}

FEED_URL = "https://calendar.google.com/calendar/ical/{cid}/public/basic.ics"

# How many days of recurring events to expand around today.
DAYS_BEHIND = 7
DAYS_AHEAD  = 100

# Event titles look like "BDII_3 [SO1]" -> room between square brackets.
ROOM_RE = re.compile(r'\s*\[.*?\]')

# IGNORE_ROOMS defines names that shouldn't be parsed as physical classrooms
IGNORE_ROOMS = {"EXAM", "EXAMEN", "ONLINE", "AULA", "TBD"}
def parse_room(summary):
    match = re.search(r'\[(.*?)\]', summary)
    if match:
        # Skip if it matches any ignored keyword
        room_name = match.group(1).strip()
        if room_name.upper() in IGNORE_ROOMS:
            return None
        return room_name
    return None


def fetch_ics(calendar_id: str) -> bytes:
    if not calendar_id.endswith("@group.calendar.google.com") and not calendar_id.endswith("@gmail.com"):
        try:
            calendar_id = base64.b64decode(calendar_id).decode('utf-8')
        except Exception:
            pass

    url = FEED_URL.format(cid=calendar_id)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        print(f"  ! could not fetch {calendar_id}: {exc}", file=sys.stderr)

        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except Exception as exc:
        return b""

def room_and_subject(summary: str, location: str):
    """Return (room, subject). The room is taken from the Google Calendar
    'Location' field if present, otherwise from the [ROOM] part of the title."""
    room = location.strip() if location else None
    m = parse_room(summary)
    if not room and m:
        room = m
    subject = ROOM_RE.sub("", summary).strip()
    return room, subject


def as_date(value):
    """icalendar returns datetime or date depending on the event type."""
    if isinstance(value, dt.datetime):
        return value.date(), value.strftime("%H:%M")
    return value, None

def main():
    today = dt.date.today()
    start = today - dt.timedelta(days=DAYS_BEHIND)
    end   = today + dt.timedelta(days=DAYS_AHEAD)

    # flatten all groups and drop duplicates (a calendar may appear on
    # more than one page)
    seen = dict()
    for group, ids in CALENDAR_GROUPS.items():
        for cid in ids:
            seen.setdefault(cid, group)
    calendars = list(seen.items())
    print(f"{len(calendars)} unique calendars | expanding events between "
          f"{start} and {end} ...")

    out, no_room = [], 0
    for cid, group in calendars:
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
                "group":   group,
                "date":    d1.isoformat(),
                "start":   t1 or "00:00",
                "end":     t2 or "23:59",
                "raw":     summary,
            })
        print(f"  ok [{group}] {cid}")

    out.sort(key=lambda e: (e["date"], e["start"], e["room"] or ""))
    data = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "timezone": "Europe/Madrid",
        "calendar_count": len(calendars),
        "event_count": len(out),
        "events": out,
    }
    with open("data.json", "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    rooms = {e["room"] for e in out if e["room"]}
    print(f"Wrote data.json: {len(out)} events, {len(rooms)} rooms "
          f"({no_room} events had no room info).")


if __name__ == "__main__":
    main()