 #!/usr/bin/env python3
"""
ESEI (UVigo) room availability scraper
======================================
Downloads the PUBLIC Google Calendar feeds that power the ESEI timetable
pages and converts them into data.json, consumed by index.html.
"""

import datetime as dt
import json
import re
import urllib.request
import urllib.error
import base64

from icalendar import Calendar
import recurring_ical_events

# ----------------------------------------------------------------------------
# 1. CONFIGURATION
# ----------------------------------------------------------------------------
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
        "ZXNlaS51dmlnby5lc19xdTUzamVuMDdvcmJhczdhYThwMWZtMzlmb0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc19wMnA1NG5wcTVhM2s5ZDZtMGk5MzIwNzhyZ0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc190amZhYXFxNzcwMmdvaDlsMGxpbnY5b3JqZ0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc19ncjhrbXE5bTdubmI2MGdiOWkyOWhrMGxha0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc19xaG1uMzIwNnFwcmRkNzcxcHRscDU0ZHRrOEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc19laTc4dm9jNnFmdGVicHQ3OWZvcTEwNmExb0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc19lbzRwYzgwc3I5bm85c2N1NGI3bW8wc25xOEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc19xa3JyYm81ZTlkNzlhMjBxNmtkc2dvbHRnY0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc18yNnVwYzYyc2hpc29qZDJ1MjNzcGFtMGJ1NEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc18yMWk3MW1uazM5djBnYzMzbzF2aW5yMXF2a0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "ZXNlaS51dmlnby5lc19oYWJ0Mm1nN29jNGE2aWVidTczaGpoaWlsb0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "c_1e7fd190617c56f14e6821faa3fd1d8ad417467dcf2b91bc42ee16aaa4f0d1cb@group.calendar.google.com",
    ],
    "Grado 1IA - 1C": [
        "Y1_k0ZnJ0MnI4MTZtcXBhbGFldGJvZjdxMThAZ3JvdXAuY2FsZW5kYXIuZ29vZ2xlLmNvbQ",
        "Y1_wdTN0NWNwa2VsNzJsMjFmcnZmb2pxcTJsMEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "Y1_wdHJrdWtpdGw2ZG9lN2RwbzVxMnBrNnR2a0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "Y1_yYXFqOGw2bG4xamxzb2I1dHIwcXNjaTU4Y0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "Y1_0c2llcG1qOWI1Z2w4b204bzVmZWVpNGFhNEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
        "esei.uvigo.es_gspvq926nhqj8pllpgtkh4j7ko@group.calendar.google.com",
    ],
    "Grado 2IA - 1C": [
        "Y1_mYzAzZTUzNjdmNjAwZDZlYTgyMjUwZDdjYTYzMGZmNmZjNzUwZDI1NGJkMTJiOWMxOGY1NzZhMjc0NGU1OGFjQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y1_kN2IxYzg4NmE2YzU2YWI2YmE3MjI4YTc3NjAwNGU4MDE0NWVlYTkzZjc2Yzc2NDQ0ZDVhMzVjZjZkZjg2NDBmQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y1_3ZTI3OGY5Mzk2ZjA0MTRhNTZjMzk0M2Y4ZjIyM2JmMzk3MTAxMzA4NzE4OTkxZDJkMTQ0MDE4YzRkMTRlYzBmQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
    ],
    "Grado 3IA - 1C": [
        "Y1_1ZDI0NDJlMGRjYzNjZjZjM2MzNDUyNzhmMmNlZDRhNWJkODBjYjEyNGUzZWYxNzI5NDE5MzE0YTZlZDA2OWU0QGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y1_mMWQyYTk4NTdmYTBiMTliOTdlNmVhZWVjYzE1ZjA1MTUxNzEzZDhmNGZiZWIwMGQ1ZTg2YTAyYTA0MGE1N2Q0QGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y1_iNTk2Y2NjMmQ3ZmQ3ZDFjMTBhNTM1N2Y5MTcxYWMzYWFlMTQ0MTMzYjY1YWI1MGRiNzUwOGVmZDAzNjNiNTMxQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y1_mZGJkNjE1ZTRmYjcxODc2NmZhODAzNWQ3NGQ5Nzg5OWI0ZWUxNTZmZjY3YTM1MjgzNzRhMTkwZGIwODA5NDczQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
    ],
    "Grado 4IA - 1C": [
        "Y1_jZGEwNGE0OGVjZWRmNzM4NjFhOWNjMDhiMTU1NGM4MjhkZDJiZjZjODZiZmIxMTVlMjJhMTFlYTk2MmZlMGMzQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y1_3ZGZlZGQ2MDdhYTRkODM2ZDJlNThlYTQ4OWI0Mzk1YzVjMDllNmZiNTE0NjNkZTNiNGFiNTMwYTkyMjZmZWMwQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y1_lNWJkZmY3ODgyMGJmZjgzMTk4MzFlYmYxZjFmMzI3M2IyZDhkMmQxNjYwMjFkYzdmNmUyOTY4NTQyNTQ5ZjQ4QGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y1_jZTNiOTQ3ODIxNjY3ZjA4MDY5NWRhNmJkY2IwNWNkZjgzMzZjZTFlZjY3ZjkyMzE2NDBmMjAzNTZkZDA2YjMwQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y1_1OTc1NDgzMDAxOGEwMzkwZmMyMTRkMTdjNWY5NTE5M2RjMmIwMTRkYzhmYmY0OWYwYmVlOGQ0NzUzN2NkYmY4QGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y1_jM2MxMzdjMjBiNTJlN2NmMWFmOWQxOTEzZjE0YTRlN2FhN2RmOGMyZDQwZjNjN2ZmNTIyMDdlMjU0NmJmYmEwQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
        "Y1_2NDNjMDBhNjE3M2RkMTE0OWRlNmY3YTQ0NDJiYzVhNjYyYzdhMTY0ZjExYjdiNTM0MzljNDMxZmE1NjNiNGViQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20",
    ],
}

FEED_URL = "https://calendar.google.com/calendar/ical/{cid}/public/basic.ics"

DAYS_BEHIND = 7
DAYS_AHEAD = 100

ROOM_RE = re.compile(r'\s*\[(.*?)\]')
IGNORE_ROOMS = {"EXAM", "EXAMEN", "ONLINE", "AULA", "TBD", "AEDII", "DAI"}

def normalize_room(room_name: str) -> str:
    if not room_name:
        return ""
    room_clean = room_name.strip()
    room_clean = re.sub(r'/elect.*$', '', room_clean, flags=re.IGNORECASE)
    if re.fullmatch(r'(aula\s+)?m[ag]{2}na', room_clean, flags=re.IGNORECASE):
        return "Aula Magna"
    return room_clean.strip()

def parse_room(summary):
    # Busca cualquier texto entre corchetes, ej: [L37], [3.2], etc.
    matches = ROOM_RE.findall(summary)
    if matches:
        # Cogemos el último corchete o el que parezca un aula válida
        for m in reversed(matches):
            room_name = normalize_room(m)
            if room_name and room_name.upper() not in IGNORE_ROOMS:
                return room_name
    return None

def room_and_subject(summary: str, location: str):
    room = None
    
    # 1. Intentar sacar el aula de la location oficial si existe
    if location:
        room = normalize_room(location)
        if room.upper() in IGNORE_ROOMS:
            room = None

    # 2. Si no hay room en location, buscar obligatoriamente en los corchetes del summary (ej: [L37])
    if not room:
        room = parse_room(summary)

    # El subject es el summary quitándole los corchetes de las aulas
    subject = ROOM_RE.sub("", summary).strip()
    return room, subject
    
def resolve_calendar_id(raw_id: str) -> str:
    """Decodes standard, UVigo-prefixed, or Y1-prefixed base64 string to a Google Calendar ID."""
    if "@group.calendar.google.com" in raw_id or "@gmail.com" in raw_id:
        return raw_id
    
    candidate = raw_id
    if candidate.startswith("Y1_"):
        candidate = candidate[3:]
    elif "_" in candidate and not candidate.startswith("esei."):
        candidate = candidate.split("_", 1)[1]
        
    try:
        padded = candidate + "=" * (-len(candidate) % 4)
        decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
        if "@" in decoded:
            return decoded
    except Exception:
        pass

    return raw_id

def fetch_ics(calendar_id: str) -> bytes:
    resolved_id = resolve_calendar_id(calendar_id)
    url = FEED_URL.format(cid=resolved_id)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception as err:
        return b""


def as_date(value):
    if isinstance(value, dt.datetime):
        return value.date(), value.strftime("%H:%M")
    return value, None

def main():
    today = dt.date.today()
    start = today - dt.timedelta(days=DAYS_BEHIND)
    end = today + dt.timedelta(days=DAYS_AHEAD)

    seen = dict()
    for group, ids in CALENDAR_GROUPS.items():
        for cid in ids:
            seen.setdefault(cid, group)
    calendars = list(seen.items())
    print(f"{len(calendars)} unique calendars | fetching events between {start} and {end} ...")

    out, no_room = [], 0
    success_count = 0

    for cid, group in calendars:
        raw = fetch_ics(cid)
        if not raw:
            continue

        try:
            cal = Calendar.from_ical(raw)
            events = recurring_ical_events.of(cal).between(start, end)
        except Exception:
            continue

        success_count += 1
        for ev in events:
            try:
                summary = str(ev.get("SUMMARY", "")).strip()
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
                    "room": room,
                    "group": group,
                    "date": d1.isoformat(),
                    "start": t1 or "00:00",
                    "end": t2 or "23:59",
                    "raw": summary,
                })
            except Exception:
                continue

        print(f"  ok [{group}] {cid[:25]}...")

    out.sort(key=lambda e: (e["date"], e["start"], e["room"] or ""))
    data = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "timezone": "Europe/Madrid",
        "calendar_count": len(calendars),
        "successful_calendars": success_count,
        "event_count": len(out),
        "events": out,
    }
    with open("data.json", "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)

    rooms = {e["room"] for e in out if e["room"]}
    print(f"\nDone! Successfully processed {success_count}/{len(calendars)} calendars.")
    print(f"Wrote data.json: {len(out)} events across {len(rooms)} unique rooms.")

if __name__ == "__main__":
    main()