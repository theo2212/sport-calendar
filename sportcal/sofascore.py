"""Source Sofascore : hand, fléchettes, esport, et tout autre sport.

On cherche l'équipe/le joueur par son nom, puis on récupère ses prochains
et derniers matchs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

from .common import DURATION_MIN, EMOJI, Event, get_json, norm, result_mark

HOSTS = ["https://www.sofascore.com/api/v1", "https://api.sofascore.com/api/v1"]
HEADERS = {"Referer": "https://www.sofascore.com/", "Origin": "https://www.sofascore.com"}

SLUG = {
    "foot": "football", "basket": "basketball", "rugby": "rugby", "hand": "handball",
    "flechettes": "darts", "esport": "esports", "tennis": "tennis", "volley": "volleyball",
    "hockey": "ice-hockey", "cyclisme": "cycling", "baseball": "baseball",
    "football-us": "american-football", "snooker": "snooker", "futsal": "futsal",
}

GAME_ALIASES = {
    "call of duty": ["call of duty", "cod"],
    "rocket league": ["rocket league", "rl"],
    "valorant": ["valorant", "valo"],
    "counter strike": ["counter strike", "cs2", "cs:go", "cs"],
    "league of legends": ["league of legends", "lol"],
}


def _api(path: str):
    errs = []
    for h in HOSTS:
        try:
            return get_json(h + path, headers=HEADERS, retries=1, pause=0.4)
        except Exception as exc:
            errs.append(str(exc))
    raise RuntimeError(" | ".join(errs))


def _search(name: str, slug: str) -> list[dict]:
    data = _api(f"/search/all?q={quote(name)}&page=0")
    out = []
    for r in data.get("results", []):
        ent = r.get("entity", r)
        if r.get("type", "team") != "team":
            continue
        if (ent.get("sport") or {}).get("slug") != slug:
            continue
        out.append(ent)
    return out


def _pick(spec: dict, cands: list[dict], sport: str) -> list[dict]:
    if not cands:
        return []
    q = norm(spec["nom"])
    exact = [c for c in cands if norm(c.get("name", "")) == q]
    pool = exact or [c for c in cands if q in norm(c.get("name", ""))] or cands
    want_gender = (spec.get("genre") or "M").upper()
    g = [c for c in pool if (c.get("gender") or want_gender).upper() == want_gender]
    pool = g or pool
    if sport == "esport":
        return pool[:8]          # une équipe par jeu
    return pool[:1]


def _game_of(ev) -> str:
    t = ev.get("tournament") or {}
    cat = (t.get("category") or {}).get("name") or ""
    return cat or (t.get("uniqueTournament") or {}).get("name", "")


def _game_ok(spec, game: str) -> bool:
    jeux = spec.get("jeux")
    if not jeux:
        return True
    g = norm(game)
    for j in jeux:
        for a in GAME_ALIASES.get(norm(j), [norm(j)]):
            if a and (f" {a} " in f" {g} "):
                return True
    return False


def fetch(sport: str, teams: list[dict], start: datetime, end: datetime, log: dict) -> list[Event]:
    slug = SLUG.get(sport, sport)
    found: dict[str, Event] = {}
    log["equipes"] = {}

    for spec in teams:
        info = log["equipes"].setdefault(spec["nom"], {})
        try:
            if spec.get("id"):
                ids = spec["id"] if isinstance(spec["id"], list) else [spec["id"]]
                entities = [{"id": i, "name": spec["nom"]} for i in ids]
            else:
                entities = _pick(spec, _search(spec["nom"], slug), sport)
        except Exception as exc:
            info["erreur"] = f"recherche : {exc}"
            continue
        if not entities:
            info["erreur"] = "introuvable sur Sofascore"
            continue
        info["trouve"] = [f"{e.get('name')} (id {e['id']})" for e in entities]
        n = 0
        for ent in entities:
            for kind in ("next", "last"):
                for page in (0, 1):
                    try:
                        data = _api(f"/team/{ent['id']}/events/{kind}/{page}")
                    except Exception as exc:
                        if page == 0 and "404" not in str(exc):
                            info.setdefault("avertissements", []).append(f"{kind}: {exc}")
                        break
                    evs = data.get("events", [])
                    for ev in evs:
                        e = _build(sport, ev, ent["id"], spec, start, end)
                        if e:
                            found[e.uid] = e
                            n += 1
                    if not data.get("hasNextPage"):
                        break
        info["matchs"] = n
    return list(found.values())


def _build(sport, ev, our_id, spec, start_w, end_w) -> Event | None:
    ts = ev.get("startTimestamp")
    if not ts:
        return None
    start = datetime.fromtimestamp(ts, tz=timezone.utc)
    if not (start_w <= start <= end_w):
        return None
    game = _game_of(ev) if sport == "esport" else ""
    if sport == "esport" and not _game_ok(spec, game):
        return None

    home, away = ev.get("homeTeam", {}), ev.get("awayTeam", {})
    hn = home.get("shortName") or home.get("name", "?")
    an = away.get("shortName") or away.get("name", "?")
    st = (ev.get("status") or {})
    stype = st.get("type", "notstarted")
    emoji = EMOJI.get(sport, "🏅")
    tag = f"[{game}] " if game else ""

    hs = (ev.get("homeScore") or {}).get("display", (ev.get("homeScore") or {}).get("current"))
    as_ = (ev.get("awayScore") or {}).get("display", (ev.get("awayScore") or {}).get("current"))

    if stype == "finished":
        state = "post"
        we_home = home.get("id") == our_id
        mark = result_mark(hs if we_home else as_, as_ if we_home else hs)
        title = f"{emoji} {tag}{hn} {hs}–{as_} {an} {mark}".strip()
    elif stype == "inprogress":
        state = "in"
        title = f"{emoji} 🔴 {tag}{hn} {hs}–{as_} {an}"
    elif stype in ("postponed", "canceled", "cancelled"):
        state = "postponed" if stype == "postponed" else "canceled"
        lab = "[Reporté]" if state == "postponed" else "[Annulé]"
        title = f"{emoji} {lab} {tag}{hn} – {an}"
    else:
        state = "pre"
        title = f"{emoji} {tag}{hn} – {an}"

    t = ev.get("tournament") or {}
    comp = (t.get("uniqueTournament") or {}).get("name") or t.get("name", "")
    desc = [f"🏆 {comp}"] if comp else []
    rnd = (ev.get("roundInfo") or {}).get("name") or (
        f"Journée {(ev.get('roundInfo') or {}).get('round')}" if (ev.get("roundInfo") or {}).get("round") else "")
    if rnd:
        desc.append(rnd)
    if st.get("description") and state != "pre":
        desc.append(f"Statut : {st['description']}")
    url = f"https://www.sofascore.com/{ev.get('slug', '')}/{ev.get('customId', '')}" if ev.get("customId") else ""

    return Event(
        uid=f"sofa-{ev['id']}", sport=sport, title=title, start=start,
        duration_min=DURATION_MIN.get(sport, 120), description="\n".join(desc),
        location=(ev.get("venue") or {}).get("name", "") if isinstance(ev.get("venue"), dict) else "",
        url=url, state=state,
    )
