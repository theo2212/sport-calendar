"""Source IBU (biathlonresults.com) : toutes les courses de Coupe du monde."""
from __future__ import annotations

from datetime import datetime, timezone

from .common import DURATION_MIN, EMOJI, Event, get_json

BASE = "https://biathlonresults.com/modules/sportapi/api"

TRAD = [
    ("Single Mixed Relay", "Relais simple mixte"), ("Mixed Relay", "Relais mixte"),
    ("Short Individual", "Individuel court"), ("Individual", "Individuel"),
    ("Mass Start", "Mass start"), ("Pursuit", "Poursuite"), ("Relay", "Relais"),
    ("Women", "Femmes"), ("Men", "Hommes"), ("Sprint", "Sprint"),
]
FLAG = {"FRA": "🇫🇷", "NOR": "🇳🇴", "SWE": "🇸🇪", "GER": "🇩🇪", "ITA": "🇮🇹", "AUT": "🇦🇹",
        "SUI": "🇨🇭", "FIN": "🇫🇮", "CZE": "🇨🇿", "USA": "🇺🇸", "CAN": "🇨🇦", "SLO": "🇸🇮",
        "UKR": "🇺🇦", "POL": "🇵🇱", "EST": "🇪🇪", "BEL": "🇧🇪", "BUL": "🇧🇬"}


def _fr(s: str) -> str:
    for en, fr in TRAD:
        s = s.replace(en, fr)
    return s


def _season_ids(start: datetime, end: datetime) -> list[str]:
    ids = set()
    for d in (start, end):
        y = d.year % 100
        ids.add(f"{y:02d}{y + 1:02d}" if d.month >= 7 else f"{y - 1:02d}{y:02d}")
    return sorted(ids)


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def fetch(start: datetime, end: datetime, log: dict) -> list[Event]:
    now = datetime.now(timezone.utc)
    out: list[Event] = []
    log["saisons"] = _season_ids(start, end)
    log["etapes"] = []
    for sid in log["saisons"]:
        events = get_json(f"{BASE}/Events", {"SeasonId": sid, "Level": 1})
        for ev in events:
            try:
                if _dt(ev["EndDate"]) < start or _dt(ev["StartDate"]) > end:
                    continue
            except Exception:
                pass
            place = ev.get("ShortDescription") or ev.get("Organizer") or ""
            log["etapes"].append(place)
            comps = get_json(f"{BASE}/Competitions", {"EventId": ev["EventId"]}, pause=0.3)
            for c in comps:
                if not c.get("StartTime"):
                    continue
                st = _dt(c["StartTime"])
                if not (start <= st <= end):
                    continue
                label = _fr(c.get("ShortDescription") or c.get("Description") or "Course")
                title = f"{EMOJI['biathlon']} {label} – {place}"
                desc = [f"🏆 {ev.get('Description', 'Coupe du monde IBU')}"]
                state = "pre"
                if st < now:
                    podium = _podium(c["RaceId"])
                    if podium:
                        state = "post"
                        title += f" · 🥇 {podium['vainqueur']}"
                        desc += podium["lignes"]
                out.append(Event(
                    uid=f"ibu-{c['RaceId']}", sport="biathlon", title=title, start=st,
                    duration_min=DURATION_MIN["biathlon"], description="\n".join(desc),
                    location=f"{place}, {ev.get('Nat', '')}".strip(", "),
                    url=f"https://www.biathlonworld.com/", state=state,
                ))
    return out


def _podium(race_id: str):
    try:
        data = get_json(f"{BASE}/Results", {"RaceId": race_id}, pause=0.3)
    except Exception:
        return None
    rows = [r for r in data.get("Results", []) if str(r.get("Rank") or "").isdigit()]
    if not rows:
        return None
    rows.sort(key=lambda r: int(r["Rank"]))

    def who(r):
        return f"{FLAG.get(r.get('Nat'), '')} {r.get('ShortName') or r.get('Name')}".strip()

    medals = ["🥇", "🥈", "🥉"]
    lines = ["", "Podium :"] + [f"{medals[i]} {who(r)} {r.get('TotalTime') or r.get('Result') or ''}".rstrip()
                                for i, r in enumerate(rows[:3])]
    fr = [r for r in rows if r.get("Nat") == "FRA"][:3]
    if fr:
        lines += ["", "🇫🇷 Français :"] + [f"{r['Rank']}e – {r.get('ShortName') or r.get('Name')}" for r in fr]
    return {"vainqueur": who(rows[0]), "lignes": lines}
