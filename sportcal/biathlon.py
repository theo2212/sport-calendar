"""Biathlon : site officiel de l'IBU (biathlonworld.com).

L'API historique (biathlonresults.com) demande désormais une authentification ;
on lit donc les données que le site public embarque dans ses pages
(`__NEXT_DATA__`) : calendrier de la saison, courses de chaque étape et,
quand elle existe, la page de résultats d'une course.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from .common import DURATION_MIN, EMOJI, Event, SESSION, UA

SITE = "https://www.biathlonworld.com"

TRAD = [
    ("Single Mixed Relay", "Relais simple mixte"), ("Mixed Relay", "Relais mixte"),
    ("Short Individual", "Individuel court"), ("Individual", "Individuel"),
    ("Mass Start", "Mass start"), ("Pursuit", "Poursuite"), ("Relay", "Relais"),
    ("Women's", "Femmes"), ("Men's", "Hommes"), ("Women", "Femmes"), ("Men", "Hommes"),
    ("(W+M)", ""), ("(M+W)", ""),
]
FLAG = {"FRA": "🇫🇷", "NOR": "🇳🇴", "SWE": "🇸🇪", "GER": "🇩🇪", "ITA": "🇮🇹", "AUT": "🇦🇹",
        "SUI": "🇨🇭", "FIN": "🇫🇮", "CZE": "🇨🇿", "USA": "🇺🇸", "CAN": "🇨🇦", "SLO": "🇸🇮",
        "UKR": "🇺🇦", "POL": "🇵🇱", "EST": "🇪🇪", "BEL": "🇧🇪", "BUL": "🇧🇬", "LAT": "🇱🇻"}


def _fr(s: str) -> str:
    for en, fr in TRAD:
        s = s.replace(en, fr)
    return " ".join(s.split())


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def _next_data(path: str) -> dict:
    r = SESSION.get(SITE + path, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    if not m:
        raise RuntimeError(f"{path} : données absentes")
    return json.loads(m.group(1))["props"]["pageProps"]


def _find_rows(obj):
    """Cherche récursivement une liste de lignes de classement (dicts avec Rank)."""
    if isinstance(obj, list) and obj and isinstance(obj[0], dict) and "Rank" in obj[0]:
        return obj
    if isinstance(obj, dict):
        it = obj.values()
    elif isinstance(obj, list):
        it = obj
    else:
        return None
    for v in it:
        r = _find_rows(v)
        if r:
            return r
    return None


def fetch(start: datetime, end: datetime, log: dict) -> list[Event]:
    now = datetime.now(timezone.utc)
    pp = _next_data("/calendar")
    events = (pp.get("eventInitialState") or {}).get("events") or []
    season = ((pp.get("seasonInitialState") or {}).get("currentSeason") or {}).get("SeasonId", "")
    log["saison"] = season
    log["etapes"] = []
    out: list[Event] = []
    for ev in events:
        try:
            if _dt(ev["EndDate"]) < start or _dt(ev["StartDate"]) > end:
                continue
        except Exception:
            continue
        place = ev.get("ShortDescription") or ev.get("Organizer") or ""
        try:
            comps = _next_data(f"/calendar?CupLevel=1&SeasonId={ev['SeasonId']}&EventId={ev['EventId']}") \
                .get("competitionsInitialState") or []
        except Exception as exc:
            log["etapes"].append(f"{place} : erreur {exc}")
            continue
        comps = [c for c in comps if str(c.get("RaceId", "")).startswith(ev["EventId"])]
        log["etapes"].append(f"{place} : {len(comps)} courses")
        champ = "Championnats du monde" if "SWRLCH" in ev["EventId"] else "Coupe du monde"
        for c in comps:
            if not c.get("StartTime"):
                continue
            st = _dt(c["StartTime"])
            if not (start <= st <= end):
                continue
            label = _fr(c.get("Description") or c.get("ShortDescription") or "Course")
            title = f"{EMOJI['biathlon']} {label} – {place}"
            desc = [f"🏆 {champ} IBU – {place} ({ev.get('NatLong', '')})"]
            state = "pre"
            if c.get("IsLive"):
                state = "in"
                title = f"{EMOJI['biathlon']} 🔴 {label} – {place}"
            elif st < now and c.get("ResultStatus") not in (None, "NONE"):
                pod = _podium(c["RaceId"])
                state = "post"
                if pod:
                    title += f" · 🥇 {pod['vainqueur']}"
                    desc += pod["lignes"]
            out.append(Event(
                uid=f"ibu-{c['RaceId']}", sport="biathlon", title=title, start=st,
                duration_min=DURATION_MIN["biathlon"], description="\n".join(desc),
                location=c.get("Location") or place, url=f"{SITE}/results/{c['RaceId']}",
                state=state,
            ))
    return out


def _podium(race_id: str):
    for path in (f"/results/{race_id}", f"/results?RaceId={race_id}"):
        try:
            rows = _find_rows(_next_data(path))
        except Exception:
            rows = None
        if rows:
            break
    else:
        return None
    rows = [r for r in rows if str(r.get("Rank") or "").isdigit()]
    if not rows:
        return None
    rows.sort(key=lambda r: int(r["Rank"]))

    def who(r):
        return f"{FLAG.get(r.get('Nat'), '')} {r.get('ShortName') or r.get('Name')}".strip()

    medals = ["🥇", "🥈", "🥉"]
    lines = ["", "Podium :"] + [f"{medals[i]} {who(r)}" for i, r in enumerate(rows[:3])]
    fr = [r for r in rows if r.get("Nat") == "FRA"][:3]
    if fr:
        lines += ["", "🇫🇷 Français :"] + [f"{r['Rank']}e – {r.get('ShortName') or r.get('Name')}" for r in fr]
    return {"vainqueur": who(rows[0]), "lignes": lines}
