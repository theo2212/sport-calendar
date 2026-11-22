"""Fléchettes : API publique du site officiel de la PDC (pdc.tv)."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .common import DURATION_MIN, EMOJI, Event, get_json, matches, result_mark

PARTICIPANTS = "https://participants.darts.web.gc.pdcservices.co.uk/v2/"
FIXTURES = "https://fixtures.darts.web.gc.pdcservices.co.uk/v2/"
LONDON = ZoneInfo("Europe/London")
H = {"Origin": "https://www.pdc.tv", "Referer": "https://www.pdc.tv/"}


def _resolve(spec):
    if spec.get("id"):
        return str(spec["id"]), spec["nom"]
    for page in range(1, 6):          # joueurs classés par ranking, 100 par page
        data = get_json(PARTICIPANTS, {"page.size": 100, "page.number": page}, headers=H)
        for p in data.get("data", []):
            a = p["attributes"]
            full = f"{a.get('firstName', '')} {a.get('lastName', '')}"
            if matches(spec["match"], full, a.get("participantSlug", "").replace("-", " ")):
                return p["id"], full
        if not (data.get("links") or {}).get("next"):
            break
    return None, None


def _pname(p):
    if not p:
        return "?"
    last = p.get("lastName") or ""
    if "confirmed" in last:
        return "À déterminer"
    return f"{(p.get('firstName') or '')[:1]}. {last}".strip(". ")


def fetch(teams: list[dict], start: datetime, end: datetime, log: dict) -> list[Event]:
    found: dict[str, Event] = {}
    log["joueurs"] = {}
    for spec in teams:
        info = log["joueurs"].setdefault(spec["nom"], {})
        pid, full = _resolve(spec)
        if not pid:
            info["erreur"] = "joueur introuvable à la PDC"
            continue
        info["trouve"] = f"{full} (id {pid})"
        n, page = 0, 1
        while page <= 20:
            data = get_json(FIXTURES, {"participantID": pid, "page.size": 100, "page.number": page}, headers=H)
            rows = data.get("data", [])
            for r in rows:
                e = _build(r, pid, start, end)
                if e and e.uid not in found:
                    found[e.uid] = e
                    n += 1
            if not rows or not (data.get("links") or {}).get("next"):
                break
            page += 1
        info["matchs"] = n
    return list(found.values())


def _build(row, pid, start_w, end_w):
    a = row["attributes"]
    try:
        local = datetime.fromisoformat(f"{a['startDate']}T{a.get('startTime') or '19:00:00'}")
        st = local.replace(tzinfo=LONDON).astimezone(timezone.utc)
    except Exception:
        return None
    if not (start_w <= st <= end_w):
        return None
    p1, p2 = a.get("participant1") or {}, a.get("participant2") or {}
    n1, n2 = _pname(p1), _pname(p2)
    s1, s2 = a.get("participant1Score"), a.get("participant2Score")
    status = (a.get("status") or "").lower()
    emoji = EMOJI["flechettes"]
    we_first = str(a.get("participant1ID")) == str(pid)

    if a.get("winnerParticipantID") or status in ("result", "completed", "finished"):
        state = "post"
        mark = "✅" if str(a.get("winnerParticipantID")) == str(pid) else (
            "❌" if a.get("winnerParticipantID") else result_mark(s1 if we_first else s2, s2 if we_first else s1))
        title = f"{emoji} {n1} {s1}–{s2} {n2} {mark}".strip()
    elif status in ("live", "inprogress", "in progress"):
        state = "in"
        title = f"{emoji} 🔴 {n1} {s1}–{s2} {n2}"
    else:
        state = "pre"
        title = f"{emoji} {n1} – {n2}"

    t = a.get("tournament") or {}
    desc = [f"🏆 {t.get('name', 'PDC')}"]
    if not a.get("startTime"):
        desc.append("⏰ Horaire à confirmer")
    info = t.get("informationPage")
    return Event(
        uid=f"pdc-{row['id']}", sport="flechettes", title=title, start=st,
        duration_min=DURATION_MIN["flechettes"] if t.get("isTelevised") else 30,
        description="\n".join(desc), location=", ".join(x for x in [t.get("venue")] if x),
        url=f"https://www.pdc.tv{info}" if info else "https://www.pdc.tv/fixtures-results", state=state,
    )
