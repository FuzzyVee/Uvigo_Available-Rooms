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

## One-time setup (≈ 10 minutes, no programming needed)

1. **Create a GitHub account** at https://github.com and click *New repository*.
   Name it `esei-rooms`, keep it **Public**, and create it.
2. **Upload the files**: in the new repo click *Add file → Upload files* and
   drag in everything from this folder (`index.html`, `scraper.py`,
   `data.json`, `requirements.txt`, and the `.github` folder).
3. **Allow the updater to write**: *Settings → Actions → General →
   Workflow permissions* → choose **Read and write permissions** → Save.
4. **Enable the website**: *Settings → Pages → Source* → **Deploy from a branch**
   → Branch `main`, folder `/(root)` → Save. Your page will be live at
   `https://<your-username>.github.io/esei-rooms/`.
5. **Run the scraper once**: go to the *Actions* tab → *Update room data* →
   *Run workflow*. Wait for the green checkmark — it will replace the sample
   `data.json` with the real timetable data.

From then on everything is automatic.

## Test the calendar feed locally (optional)

The scraper reads the same public feed Google Calendar uses:

```
https://calendar.google.com/calendar/ical/esei.uvigo.es_gq96dj81nddqrptf1ohm38lvtg@group.calendar.google.com/public/basic.ics
```

Paste that URL in a browser — if a file downloads, the feed is public and the
scraper will work. (If you get an error page instead, the school restricted
the calendar, and the page can only show the sample data.)

## Adding other years / rooms

Each ESEI year page embeds its own calendar(s). To cover the whole building,
repeat what you did for 3rd year for the other years: open the page, F12 →
Elements, copy the `<iframe>` tag, and add every `src=...` calendar ID to the
`CALENDARS` list in `scraper.py`.

## Local development

```bash
pip install -r requirements.txt
python scraper.py          # writes data.json
python -m http.server      # open http://localhost:8000
```

*Note: `data.json` currently contains SAMPLE data so the page renders
immediately — step 5 of the setup replaces it with real data.*
