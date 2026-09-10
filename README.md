# ESEI Room Availability

A small personal page that shows which ESEI (UVigo) rooms are **free or busy**,
built from the official public Google Calendars that power the school's
timetable pages.

## How it works

```
Google Calendar (public .ics feeds, maintained by ESEI)
        │
        ▼  every 6 hours (GitHub Action, free)
   scraper.py  ──►  data.json
        │
        ▼  hosted on GitHub Pages (free)
   index.html  ──►  "Room SO1: BUSY (BDII_3 until 10:30) · Next: 12:30 IU_7"
```

No server, no database, no API keys. If the school changes a timetable,
your page picks it up automatically within 6 hours.
