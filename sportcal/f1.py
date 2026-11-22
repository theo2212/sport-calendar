"""Source Jolpica (successeur d'Ergast) : Grands Prix de F1 + podium."""
from __future__ import annotations

from datetime import datetime, timezone

from .common import DURATION_MIN, EMOJI, Event, get_json

BASE = "https://api.jolpi.ca/ergast/f1"
FR = {
    "Australian": "Australie", "Chinese": "Chine", "Japanese": "Japon", "Bahrain": "Bahreïn",
    "Saudi Arabian": "Arabie saoudite", "Miami": "Miami", "Canadian": "Canada", "Monaco": "Monaco",
    "Spanish": "Espagne", "Barcelona-Catalunya": "Barcelone", "Austrian": "Autriche",
    "British": "Grande-Bretagne", "Belgian": "Belgique", "Hungarian": "Hongrie", "Dutch": "Pays-Bas",
    "Italian": "Italie", "Madrid": "Madrid", "Azerbaijan": "Azerbaïdjan", "Singapore": "Singapour",
    "United States": "États-Unis", "Mexico City": "Mexico", "São Paulo": "Brésil", "Brazilian": "Brésil",
    "Las Vegas": "Las Vegas", "Qatar": "Qatar", "Abu Dhabi": "Abu Dhabi", "Emilia Romagna": "Émilie-Romagne",
}


def fetch(start: datetime, end: datetime, log: dict) -> list[Event]:
    now = datetime.now(timezone.utc)
    out = []
    for year in sorted({start.year, end.year}):
        try:
            data = get_json(f"{BASE}/{year}.json", {"limit": 100}, pause=0.3)
        except Exception as exc:
            log.setdefault("avertissements", []).append(str(exc))
            continue
        races = data["MRData"]["RaceTable"]["Races"]
        log[str(year)] = len(races)
        for r in races:
            tbc = not r.get("time")
            st = datetime.fromisoformat(f"{r['date']}T{r.get('time', '14:00:00Z')}".replace("Z", "+00:00"))
            st = st.astimezone(timezone.utc)
            if not (start <= st <= end):
                continue
            name = r["raceName"].replace(" Grand Prix", "")
            name = FR.get(name, name)
            loc = r.get("Circuit", {})
            title = f"{EMOJI['f1']} GP {name}"
            desc = [f"🏆 Formule 1 {year} – manche {r['round']}", loc.get("circuitName", "")]
            if tbc:
                desc.append("⏰ Horaire à confirmer")
            state = "pre"
            if st < now:
                pod = _podium(year, r["round"])
                if pod:
                    state = "post"
                    title += f" · 🏆 {pod[0]}"
                    desc += ["", "Podium :"] + [f"{m} {p}" for m, p in zip(["🥇", "🥈", "🥉"], pod)]
            l = loc.get("Location", {})
            out.append(Event(
                uid=f"f1-{year}-{r['round']}", sport="f1", title=title, start=st,
                duration_min=DURATION_MIN["f1"], description="\n".join(x for x in desc if x is not None),
                location=", ".join(x for x in [l.get("locality"), l.get("country")] if x),
                url=r.get("url", ""), state=state,
            ))
    return out


def _podium(year, rnd):
    try:
        data = get_json(f"{BASE}/{year}/{rnd}/results.json", {"limit": 3}, pause=0.3)
        res = data["MRData"]["RaceTable"]["Races"][0]["Results"][:3]
    except Exception:
        return None
    return [f"{x['Driver']['familyName']} ({x['Constructor']['name']})" for x in res]
