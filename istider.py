#!/usr/bin/env python3
import re
import datetime
import urllib.request

RBOK_URL = "https://nacka.rbok.se/informationstavla?id=a4d7b5df-2c80-409f-ac9d-da8d6366284b"
TIMEZONE = "Europe/Stockholm"
OUTPUT_FILE = "istider.ics"

def fetch_html(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Nacka-Istider-ICS/1.0"}
    )
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def strip_html(html):
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"\s+", " ", html)
    return html.strip()

def month_name_to_index(m):
    mapping = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }
    return mapping.get(m, None)

def guess_datetime(base, day, month, time_str):
    hour, minute = map(int, time_str.split(":"))
    year = base.year
    dt = datetime.datetime(year, month, day, hour, minute)

    if (dt - base).days < -200:
        dt = datetime.datetime(year + 1, month, day, hour, minute)
    return dt

def parse_events(text):
    events = []

    pattern = re.compile(
        r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec),\s+"
        r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2}),\s*"
        r"([^,]+(?:/[^,]+)?)[,\s]+([^\.]+)\.?",
        re.I
    )

    now = datetime.datetime.now()

    for match in pattern.finditer(text):
        weekday, day_str, month_str, start_time, end_time, location_raw, info_raw = match.groups()

        day = int(day_str)
        month = month_name_to_index(month_str)
        if not month:
            continue

        start = guess_datetime(now, day, month, start_time)
        end = guess_datetime(now, day, month, end_time)

        location = location_raw.strip()
        info = info_raw.strip()

        summary = info
        if "Allmänhetens åkning" not in summary:
            summary = f"Allmänhetens åkning – {info}"

        events.append({
            "summary": summary,
            "description": info,
            "location": location,
            "start": start,
            "end": end,
        })

    return events

def format_ics_datetime(dt, utc=False):
    if utc:
        dt = dt.astimezone(datetime.timezone.utc)
        return dt.strftime("%Y%m%dT%H%M%SZ")
    else:
        return dt.strftime("%Y%m%dT%H%M%S")

def escape_ics(text):
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
        .replace("\r", "")
    )

def make_uid(ev):
    base = f"{ev['start'].isoformat()}-{ev['location']}-{ev['summary']}"
    h = 0
    for ch in base:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return f"nacka-{h}@istider"

def build_ics(events):
    now = datetime.datetime.now(datetime.timezone.utc)
    dtstamp = format_ics_datetime(now, utc=True)

    lines = []
    lines.append("BEGIN:VCALENDAR")
    lines.append("VERSION:2.0")
    lines.append("PRODID:-//Nacka Istider//GitHub Actions//SV")
    lines.append("CALSCALE:GREGORIAN")
    lines.append("METHOD:PUBLISH")

    for ev in events:
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{make_uid(ev)}")
        lines.append(f"DTSTAMP:{dtstamp}")
        lines.append(f"SUMMARY:{escape_ics(ev['summary'])}")
        lines.append(f"DESCRIPTION:{escape_ics(ev['description'])}")
        lines.append(f"LOCATION:{escape_ics(ev['location'])}")
        lines.append(f"DTSTART;TZID={TIMEZONE}:{format_ics_datetime(ev['start'])}")
        lines.append(f"DTEND;TZID={TIMEZONE}:{format_ics_datetime(ev['end'])}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)

def main():
    html = fetch_html(RBOK_URL)
    text = strip_html(html)
    events = parse_events(text)
    ics = build_ics(events)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(ics)

    print(f"Skrev {len(events)} events till {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
