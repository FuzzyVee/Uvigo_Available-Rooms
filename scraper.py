#!/usr/bin/env python3
"""
ESEI (UVigo) room availability scraper
======================================
Downloads the PUBLIC Google Calendar feeds that power the ESEI timetable
pages and converts them into data.json, consumed by index.html.

Now also includes the room occupancy calendars published at the
"Ocupación Aulas" page, ignoring duplicate calendars and duplicate events
(the same class often appears in both a degree calendar and a room calendar).
"""

import datetime as dt
import json
import re
import urllib.request
import urllib.error
import urllib.parse
import base64
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

from icalendar import Calendar
import recurring_ical_events

MADRID = ZoneInfo("Europe/Madrid")

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

# --- Room occupancy calendars ("Ocupación Aulas" page) ----------------------
OCCUPATION_PAGE_URL = (
    "https://esei.uvigo.es/a-esei/formularios/formularios-xerais/ocupacion-aulas/"
)
ROOM_GROUP = "Ocupación Aulas"

# Static fallback used only if the page cannot be fetched (kept in sync with
# the page on 2026-10-15). Calendar IDs are the URL-decoded `src` params.
ROOM_CALENDARS_FALLBACK = {
    "Aula 2.1": "c_8215f375fc0a944d31f42dc3231170b3cf879554c2ddd2e77b06a78974fced0f@group.calendar.google.com",
    "Aula 2.2": "c_c9a41a2e44e97156defe4dc92b01bef3b43f3886fa232ae116ad84d0e718eb5f@group.calendar.google.com",
    "Aula 2.3": "c_123343ae7f11145134f7aec809823a45e4969aa91825036e3ba7726bd657375d@group.calendar.google.com",
    "Aula 2.4": "c_aa070625afae045422da4fd27812664a189a56d6ff25649057984803985524b6@group.calendar.google.com",
    "Aula 3.1": "c_0b5df87827a29b7b8271e9e9a64938ab8796b2e4b091eedf4813b34f423a895f@group.calendar.google.com",
    "Aula 3.2": "c_2b5751f74b1c7bd28521a78794b8eec2ba71246679da9f4e0646863b7ca5a833@group.calendar.google.com",
    "Lab Automática": "c_a1d997bc3f825f667521a37bbd8813180b8c9128e49b207c46e372399879b1ff@group.calendar.google.com",
    "Lab B00": "c_436f7fb7f99bb4df523f823eb94bf9601aa5a11377a96fa770fbf414e9f398c4@group.calendar.google.com",
    "Lab Electrónica": "c_df4d2653988ab6c7f8a9820fd952218a3db5c8a9e4574cfcb8f419158b3f9cbe@group.calendar.google.com",
    "Lab L30A": "c_ea163595f487efaa561531f687c5c942e1d799aad183e697d8d3a943b2c8a91d@group.calendar.google.com",
    "Lab L31A": "c_81cf471ce806905264912f46fff7607a4d5a7b9a573bcb216ed6f04b3066e7d4@group.calendar.google.com",
    "Lab L31B": "c_9cf1b3cca3b9cbe5f23767521ee66ec151d8c112d3317af323c99261be685f21@group.calendar.google.com",
    "Lab L37": "c_9e4f901bb22c3d23b98c43879ce536d690cc7811c7760c21f517cd2d229838d2@group.calendar.google.com",
    "Lab L38": "c_58498da7f4fff9ed447ef474c5e126aff6e6833e61aef705726f29ea94afb78a@group.calendar.google.com",
    "Lab SO1": "c_bfd0cced0b08ad3301ac0441f7c967b03d71d06ec65ebe6f75c4febf6908c975@group.calendar.google.com",
    "Lab SO2": "c_7166f84b219f6000fb71ade7ebac82eccddeac8a938bbce447f59fa154704108@group.calendar.google.com",
    "Lab SO3": "c_b3e3d2876ee946ca7569b3bb163c4e6f476009591e754e70a921562d8f6ac3bf@group.calendar.google.com",
    "Lab SO4": "c_b575659ca23de662b1217cd55eab03740087cb9a53a7cfd41f56e06f8ed2c2c7@group.calendar.google.com",
    "Lab SO5": "c_29081c482f530acee4d3747b5dff28d9b02440ab0d9785abda54b803672ce939@group.calendar.google.com",
    "Lab SO6": "c_4f6e486262b6ba784f1ac8d9a27dc0f4649835cb656becfd1eee55e819369648@group.calendar.google.com",
    "Lab SO7": "c_ff47ba72e5dd5435020e205567614c5a3fba0d77b89ee5c394b8e4289a9a9b4c@group.calendar.google.com",
    "Lab SO8": "c_1edbc5812f08fe17337ec630ef23d582b3a117a3ab251f0b499000c0f8aad67c@group.calendar.google.com",
    "Lab SO9": "c_f3fea1b3231402164781e9d936ad85a0e90b9206ed3cd604ee17e533d9a192e4@group.calendar.google.com",
    "Aula Magna": "c_79bbb2b2a6c515296a484392ef5f86e080f2addab8b11ea7885789c87408742a@group.calendar.google.com",
    "Seminario 40": "c_647b65202ee7154033919eb964d07113718fc19089d4f7cb2a4671abb603febc@group.calendar.google.com",
    "Salón de Actos": "c_c4efacaeca60bc6e5fa3864fce4c374f3e4d06aad1510de9d968a4cfb0fb8d8b@group.calendar.google.com",
    "Salón de Graos": "c_7cd2ac0c8b68426f81f5e321abd4ae727cbb25b9b907352c5518d319856875ab@group.calendar.google.com",
    "Sala de Xuntas": "c_41d80fa80ecbcf291ed5f99ae646e96766d0b4ba50046ba0e95c8eef312c5fd5@group.calendar.google.com",
}

FEED_URL = "https://calendar.google.com/calendar/ical/{cid}/public/basic.ics"

DAYS_BEHIND = 7
DAYS_AHEAD = 100

ROOM_RE = re.compile(r'\s*\[(.*?)\]')
IGNORE_ROOMS = {"EXAM", "EXAMEN", "ONLINE", "AULA", "TBD", "AEDII", "DAI"}

# Room codes as they appear in brackets: 2.1, L37, SO4, B00, L31A, Autom, Magna...
ROOM_CODE_RE = re.compile(r'^(?:\d\.\d|[A-Za-z]{1,3}\d{1,3}[A-Za-z]?|AUTOM|MAGNA)$', re.IGNORECASE)

# Aliases so the same physical room always maps to the same key
ROOM_KEY_ALIASES = {
    "AUTOMATICA": "AUTOM",
    "AUTOMÁTICA": "AUTOM",
}

def normalize_room(room_name: str) -> str:
    if not room_name:
        return ""
    room_clean = room_name.strip()
    room_clean = re.sub(r'/elect.*$', '', room_clean, flags=re.IGNORECASE)
    if re.fullmatch(r'(aula\s+)?m[ag]{2}na', room_clean, flags=re.IGNORECASE):
        return "Aula Magna"
    # 'Aula 2.1' -> '2.1', 'Lab SO9' -> 'SO9', 'Laboratorio de X' -> 'X'
    room_clean = re.sub(
        r'^(?:aula|lab|laboratorio(?:\s+de)?)\s+(?=\S)',
        '', room_clean, count=1, flags=re.IGNORECASE,
    )
    return room_clean.strip()

def room_key(room_name: str) -> str:
    """Canonical key used to compare rooms across feeds ([Autom] vs [AUTOM], 'Aula 2.1' vs '2.1')."""
    key = re.sub(r'\s+', ' ', (room_name or '').strip()).upper()
    # 'AULA 2.1' -> '2.1', 'LAB AUTOMÁTICA'/'LABORATORIO DE AUTOMÁTICA' -> 'AUTOMÁTICA'
    key = re.sub(r'^AULA\s+(?=\S)', '', key)
    key = re.sub(r'^(LAB|LABORATORIO)(\s+DE)?\s+', '', key)
    # 'SALA DE XUNTAS' == 'SALA XUNTAS', 'SALÓN DE ACTOS' == 'SALÓN ACTOS'
    key = re.sub(r'\bDE\b\s*', '', key)
    key = re.sub(r'\s+', ' ', key).strip()
    return ROOM_KEY_ALIASES.get(key, key)

def parse_room(summary):
    # Busca cualquier texto entre corchetes, ej: [L37], [3.2], etc.
    matches = ROOM_RE.findall(summary)
    valid = []
    for m in matches:
        room_name = normalize_room(m)
        if room_name and room_name.upper() not in IGNORE_ROOMS:
            valid.append(room_name)
    if not valid:
        return None
    # Prefer the first bracket that looks like a room code; summaries such as
    # 'DAGSS_1 [SO4] [DEFENSA PROYECTO]' put the room FIRST and an activity
    # type last, so the old 'last bracket' rule picked up junk rooms.
    for room_name in valid:
        if ROOM_CODE_RE.match(room_name):
            return room_name
    # Fallback: keep the old behaviour (last non-ignored bracket)
    return valid[-1]

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

# ----------------------------------------------------------------------------
# 2. ROOM CALENDAR DISCOVERY (from the "Ocupación Aulas" page)
# ----------------------------------------------------------------------------
class _EmbedLinkParser(HTMLParser):
    """Collects (room label, calendar id) pairs from Google Calendar embed links."""

    EMBED_RE = re.compile(r'calendar\.google\.com/calendar/embed', re.IGNORECASE)

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found = []          # list of (label, calendar_id)
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self._record(self._href, "".join(self._text).strip())
            self._href = None
            self._text = []

    def _record(self, href, label):
        if not self.EMBED_RE.search(href):
            return
        parsed = urllib.parse.urlparse(href)
        params = urllib.parse.parse_qs(parsed.query)
        src = params.get("src", [None])[0]
        if src:
            self.found.append((label or src, src))

def fetch_page(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")

def discover_room_calendars() -> dict:
    """Fetches the 'Ocupación Aulas' page and returns {room label: calendar id}.

    Falls back to the static ROOM_CALENDARS_FALLBACK list if the page cannot
    be fetched or contains no calendar links.
    """
    try:
        html = fetch_page(OCCUPATION_PAGE_URL)
        parser = _EmbedLinkParser()
        parser.feed(html)
        rooms = {label: cid for label, cid in parser.found if cid}
        if rooms:
            print(f"Discovered {len(rooms)} room calendars on the occupation page.")
            return rooms
        print("Occupation page fetched but no calendar links found; using static list.")
    except Exception as err:
        print(f"Could not fetch occupation page ({err}); using static list.")
    return dict(ROOM_CALENDARS_FALLBACK)

# ----------------------------------------------------------------------------
# 3. FETCHING / PARSING
# ----------------------------------------------------------------------------
def fetch_ics(calendar_id: str) -> bytes:
    resolved_id = resolve_calendar_id(calendar_id)
    url = FEED_URL.format(cid=urllib.parse.quote(resolved_id, safe="@"))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception as err:
        print(f"  !! fetch failed for {resolved_id[:40]}...: {err}")
        return b""

def as_date(value):
    if isinstance(value, dt.datetime):
        if value.tzinfo is not None:
            # Normalize to Europe/Madrid so UTC and TZID events compare equal
            value = value.astimezone(MADRID)
        return value.date(), value.strftime("%H:%M")
    return value, None

def annotated_subject(event: dict) -> str:
    """Subject with room brackets removed but activity annotations kept.

    'DAGSS_2 [SO3] [EXAMEN DE PROGRAMACIÓN]' with room SO3 -> 'dagss_2 [examen de programación]'
    'DAGSS_2 [SO3]' with room SO3 -> 'dagss_2'
    """
    full, _annot = subject_parts(event)
    return full

def subject_parts(event: dict) -> tuple:
    """Returns (full annotated subject, annotation-only string), both casefolded.

    The annotation part keeps activity brackets such as '[EXAMEN DE PROGRAMACIÓN]'
    so an exam and a project defense in the same slot stay distinct events.
    """
    raw = event["raw"] or ""
    rk = room_key(event["room"])
    if not rk:
        # No room info: keep all brackets so we never over-merge
        return re.sub(r'\s+', ' ', raw).strip().casefold(), re.sub(r'\s+', ' ', raw).strip().casefold()

    kept = []

    def repl(m):
        inner = m.group(1)
        if room_key(normalize_room(inner)) == rk:
            return " "
        kept.append(f"[{inner}]")
        return f"[{inner}]"

    full = re.sub(r'\s+', ' ', re.sub(r'\s*\[(.*?)\]', repl, raw)).strip().casefold()
    return full, " ".join(kept).strip().casefold()

class DuplicateTracker:
    """Deduplication with annotation and source awareness.

    - Identical events (same subject incl. annotations, room, slot) -> duplicate.
    - A degree-feed copy and a room-feed copy of the same booking, where one
      omits the activity annotations (e.g. 'DAGSS_2 [SO3] [EXAMEN DE PROGRAMACIÓN]'
      vs 'DAGSS_2 [SO3]') -> duplicate (merged).
    - Same subject/room/slot but DIFFERENT explicit annotations (an exam vs a
      project defense) -> two distinct events (both kept), regardless of order.
    """

    def __init__(self):
        self.exact = set()   # (annotated subject, room key, date, start, end)
        self.base = {}       # (clean subject, room key, date, start, end) -> [(annot, source)]
        self.skipped = 0

    def add(self, event: dict, source: str = "degree") -> bool:
        """Register an event; returns True if it is new (keep it), False if duplicate.

        `source` is "degree" for degree calendars and "room" for the occupancy
        calendars; the annotation-omission merge is only allowed across the two.
        """
        ann, annot = subject_parts(event)
        rk = room_key(event["room"])
        clean = re.sub(r'\s+', ' ', event["subject"] or "").strip().casefold()
        exact = (ann, rk, event["date"], event["start"], event["end"])
        base = (clean, rk, event["date"], event["start"], event["end"])

        if exact in self.exact:
            self.skipped += 1
            return False
        for other_annot, other_source in self.base.get(base, []):
            if other_source != source and (not annot or not other_annot):
                # Same booking seen from the other feed kind, one copy without
                # annotations (typically the room calendar's copy of an
                # annotated degree-feed event).
                self.skipped += 1
                return False

        self.exact.add(exact)
        self.base.setdefault(base, []).append((annot, source))
        return True

def main():
    today = dt.date.today()
    start = today - dt.timedelta(days=DAYS_BEHIND)
    end = today + dt.timedelta(days=DAYS_AHEAD)

    # --- Build calendar list, deduplicated by RESOLVED id --------------------
    # calendars: {resolved_id: (group, room_label or None)}
    calendars = {}
    for group, ids in CALENDAR_GROUPS.items():
        for cid in ids:
            resolved = resolve_calendar_id(cid)
            calendars.setdefault(resolved, (group, None))

    room_cals = discover_room_calendars()
    for label, cid in room_cals.items():
        resolved = resolve_calendar_id(cid)
        group, existing_label = calendars.get(resolved, (ROOM_GROUP, None))
        # Keep the degree group if this calendar is already scraped; but always
        # remember the room it belongs to.
        calendars[resolved] = (group, existing_label or label)

    print(f"{len(calendars)} unique calendars | fetching events between {start} and {end} ...")

    out, no_room = [], 0
    success_count = 0
    duplicate_calendars = 0
    tracker = DuplicateTracker()
    room_fallback_used = 0
    # Canonical display name per room key (first-seen wins; degree feeds are
    # processed first, so e.g. '2.1' is preferred over 'Aula 2.1').
    display_names = {}
    # Seed with the official labels from the occupation page
    for label in room_cals:
        short = normalize_room(label)
        display_names.setdefault(room_key(short), short)

    for resolved_id, (group, room_label) in calendars.items():
        raw = fetch_ics(resolved_id)
        if not raw:
            continue

        try:
            cal = Calendar.from_ical(raw)
            events = recurring_ical_events.of(cal).between(start, end)
        except Exception as err:
            print(f"  !! parse failed for {resolved_id[:40]}...: {err}")
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
                if not room and room_label:
                    # Event from a room calendar with no room info: it belongs
                    # to the room whose calendar we are reading.
                    room = normalize_room(room_label)
                    room_fallback_used += 1
                if not room:
                    no_room += 1
                if room:
                    room = display_names.setdefault(room_key(room), room)
                event = {
                    "subject": subject,
                    "room": room,
                    "group": group,
                    "date": d1.isoformat(),
                    "start": t1 or "00:00",
                    "end": t2 or "23:59",
                    "raw": summary,
                }
                if not tracker.add(event, source="room" if room_label else "degree"):
                    # Degree feeds are processed first, so their (group, room
                    # naming) win; room-calendar copies are dropped.
                    continue
                out.append(event)
            except Exception:
                continue

        tag = f" [{room_label}]" if room_label else ""
        print(f"  ok [{group}]{tag} {resolved_id[:25]}...")

    out.sort(key=lambda e: (e["date"], e["start"], e["room"] or ""))
    data = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "timezone": "Europe/Madrid",
        "calendar_count": len(calendars),
        "successful_calendars": success_count,
        "event_count": len(out),
        "duplicate_events_skipped": tracker.skipped,
        "room_calendars": {label: resolve_calendar_id(cid) for label, cid in room_cals.items()},
        "events": out,
    }
    with open("data.json", "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)

    rooms = {e["room"] for e in out if e["room"]}
    print(f"\nDone! Successfully processed {success_count}/{len(calendars)} calendars.")
    print(f"Wrote data.json: {len(out)} events across {len(rooms)} unique rooms.")
    print(f"Skipped {tracker.skipped} duplicate events; room fallback used {room_fallback_used} times.")

if __name__ == "__main__":
    main()
