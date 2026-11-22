"""Écriture iCalendar (RFC 5545) sans dépendance."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _esc(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    out, cur = [], b""
    for ch in line:
        b = ch.encode()
        if len(cur) + len(b) > 73:
            out.append(cur.decode())
            cur = b" " + b
        else:
            cur += b
    out.append(cur.decode())
    return "\r\n".join(out)


def _fmt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build(name: str, items: list[dict], color: str = "") -> str:
    """items : [{"event": Event, "seq": int, "modified": datetime}]"""
    now = _fmt(datetime.now(timezone.utc))
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//theo2212//sport-calendar//FR",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_esc(name)}", "X-WR-TIMEZONE:Europe/Paris",
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H", "X-PUBLISHED-TTL:PT1H",
    ]
    if color:
        lines.append(f"X-APPLE-CALENDAR-COLOR:{color}")
    for it in sorted(items, key=lambda x: x["event"].start):
        e = it["event"]
        desc = e.description + (f"\n\n🔗 {e.url}" if e.url else "")
        lines += [
            "BEGIN:VEVENT",
            f"UID:{e.uid}@sport-calendar",
            f"DTSTAMP:{now}",
            f"LAST-MODIFIED:{_fmt(it['modified'])}",
            f"SEQUENCE:{it['seq']}",
            f"DTSTART:{_fmt(e.start)}",
            f"DTEND:{_fmt(e.start + timedelta(minutes=e.duration_min))}",
            f"SUMMARY:{_esc(e.title)}",
            f"DESCRIPTION:{_esc(desc)}",
        ]
        if e.location:
            lines.append(f"LOCATION:{_esc(e.location)}")
        if e.url:
            lines.append(f"URL:{e.url}")
        lines += [
            "STATUS:" + ("CANCELLED" if e.state == "canceled" else "TENTATIVE" if e.state == "postponed" else "CONFIRMED"),
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(l) for l in lines) + "\r\n"
