"""Source TheSportsDB (clé gratuite) : hand, fléchettes et tout autre sport.

Limite gratuite ≈ 30 requêtes/min → on temporise.
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

from .common import DURATION_MIN, EMOJI, Event, get_json, matches, norm, result_mark

T = "https://www.thesportsdb.com/api/v1/json/123"
SPORT_NAME = {
    "hand": "Handball", "flechettes": "Darts", "foot": "Soccer", "basket": "Basketball",
    "rugby": "Rugby", "tennis": "Tennis", "volley": "Volleyball", "hockey": "Ice Hockey",
    "cyclisme": "Cycling", "baseball": "Baseball", "football-us": "American Football",
    "esport": "Esports", "golf": "Golf",
}
FINISHED = {"match finished", "ft", "aet", "ap", "finished", "aot"}


def _get(path):
    return get_json(T + path, retries=3, pause=2.3)


def _resolve(spec, sport_name):
    if spec.get("id"):
        return {"idTeam": spec["id"], "strTeam": spec["nom"]}, None
    queries = [spec["nom"], f"{spec['nom']} {sport_name}"]
    for q in queries:
        teams = (_get(f"/searchteams.php?t={quote(q)}") or {}).get("teams") or []
        teams = [t for t in teams if t.get("strSport") == sport_name]
        want = "Female" if str(spec.get("genre", "M")).upper() == "F" else "Male"
        g = [t for t in teams if (t.get("strGender") or want) == want]
        if g or teams:
            return (g or teams)[0], None
    # Joueur individuel (fléchettes, tennis…) : on suit son « équipe » et on filtre sur son nom
    players = (_get(f"/searchplayers.php?p={quote(spec['nom'])}") or {}).get("player") or []
    players = [p for p in players if p.get("strSport") == sport_name]
    if players and players[0].get("idTeam"):
        p = players[0]
        return {"idTeam": p["idTeam"], "strTeam": p.get("strTeam", "")}, p["strPlayer"]
    return None, None


def fetch(sport: str, teams: list[dict], start: datetime, end: datetime, log: dict) -> list[Event]:
    sport_name = SPORT_NAME.get(sport, sport.capitalize())
    found: dict[str, Event] = {}
    log["equipes"] = {}
    for spec in teams:
        info = log["equipes"].setdefault(spec["nom"], {})
        try:
            team, player = _resolve(spec, sport_name)
        except Exception as exc:
            info["erreur"] = f"recherche : {exc}"
            continue
        if not team:
            info["erreur"] = "introuvable sur TheSportsDB"
            continue
        info["trouve"] = f"{team.get('strTeam')} (id {team['idTeam']})" + (f" – joueur {player}" if player else "")
        n = 0
        for ep, key in (("eventsnext", "events"), ("eventslast", "results")):
            try:
                data = _get(f"/{ep}.php?id={team['idTeam']}") or {}
            except Exception as exc:
                info.setdefault("avertissements", []).append(f"{ep}: {exc}")
                continue
            for ev in data.get(key) or data.get("events") or []:
                if player and not matches([player, player.split()[-1]], ev.get("strEvent", "")):
                    continue
                e = _build(sport, ev, team, start, end)
                if e and e.uid not in found:
                    found[e.uid] = e
                    n += 1
        info["matchs"] = n
    return list(found.values())


def _build(sport, ev, team, start_w, end_w):
    ts = ev.get("strTimestamp")
    try:
        if ts:
            start = datetime.fromisoformat(ts.replace("Z", "")).replace(tzinfo=timezone.utc)
        else:
            start = datetime.fromisoformat(f"{ev['dateEvent']}T{(ev.get('strTime') or '12:00:00')[:8]}").replace(tzinfo=timezone.utc)
    except Exception:
        return None
    if not (start_w <= start <= end_w):
        return None
    emoji = EMOJI.get(sport, "🏅")
    h, a = ev.get("strHomeTeam") or "", ev.get("strAwayTeam") or ""
    hs, as_ = ev.get("intHomeScore"), ev.get("intAwayScore")
    status = norm(ev.get("strStatus") or "")
    postponed = str(ev.get("strPostponed", "")).lower() == "yes"

    if postponed:
        state, title = "postponed", f"{emoji} [Reporté] {h} – {a}"
    elif hs not in (None, "") and as_ not in (None, "") and (status in FINISHED or start < datetime.now(timezone.utc)):
        state = "post"
        we_home = norm(team.get("strTeam", "")) == norm(h)
        mark = result_mark(hs if we_home else as_, as_ if we_home else hs) if h and a else ""
        title = f"{emoji} {h} {hs}–{as_} {a} {mark}".strip()
    else:
        state = "pre"
        title = f"{emoji} {h} – {a}" if h and a else f"{emoji} {ev.get('strEvent', '')}"

    desc = [f"🏆 {ev['strLeague']}"] if ev.get("strLeague") else []
    if ev.get("intRound"):
        desc.append(f"Journée {ev['intRound']}")
    return Event(
        uid=f"tsdb-{ev['idEvent']}", sport=sport, title=title, start=start,
        duration_min=DURATION_MIN.get(sport, 120), description="\n".join(desc),
        location=ev.get("strVenue") or "", url="", state=state,
    )
