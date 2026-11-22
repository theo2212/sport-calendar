"""Source ESPN (API publique du site) : foot, basket, rugby.

On interroge le « scoreboard » de chaque compétition par tranches de dates
puis on garde les matchs où joue une équipe suivie. Pas besoin d'identifiant :
le nom suffit.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .common import DURATION_MIN, EMOJI, Event, get_json, matches, result_mark

BASE = "https://site.api.espn.com/apis/site/v2/sports"
SPORT_PATH = {"foot": "soccer", "basket": "basketball", "rugby": "rugby"}

# Compétitions parcourues par défaut (complétables par équipe avec `ligues:`)
DEFAULT_LEAGUES = {
    "foot": [
        "fra.1", "fra.coupe_de_france", "fra.super_cup",
        "uefa.champions", "uefa.europa", "uefa.europa.conf",
        "uefa.nations", "fifa.friendly", "fifa.worldq.uefa", "uefa.euroq",
        "fifa.world", "uefa.euro",
    ],
    "basket": ["nba"],
    "rugby": [
        "270559",  # Top 14
        "271937",  # Champions Cup
        "272073",  # Challenge Cup
        "180659",  # Six Nations
        "289234",  # Tests internationaux
        "164205",  # Coupe du monde
    ],
}


def _chunks(start: datetime, end: datetime, days: int = 28):
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=days), end)
        yield cur, nxt
        cur = nxt + timedelta(days=1)


def _score(c):
    s = c.get("score")
    if isinstance(s, dict):
        return s.get("displayValue") or s.get("value")
    return s


def _name(c):
    t = c.get("team", {})
    return t.get("shortDisplayName") or t.get("displayName") or t.get("name") or "?"


def _all_names(c):
    t = c.get("team", {})
    return [t.get(k, "") for k in ("displayName", "shortDisplayName", "name", "location", "nickname")]


def fetch(sport: str, teams: list[dict], start: datetime, end: datetime, log: dict) -> list[Event]:
    path = SPORT_PATH[sport]
    leagues = list(DEFAULT_LEAGUES[sport])
    for t in teams:
        for lg in t.get("ligues", []) or []:
            if str(lg) not in leagues:
                leagues.append(str(lg))

    found: dict[str, Event] = {}
    per_team = {t["nom"]: 0 for t in teams}
    log["ligues"] = {}

    for lg in leagues:
        n_ev, err = 0, None
        for s, e in _chunks(start, end):
            try:
                data = get_json(f"{BASE}/{path}/{lg}/scoreboard",
                                {"dates": f"{s:%Y%m%d}-{e:%Y%m%d}", "limit": 1000})
            except Exception as exc:
                err = str(exc)
                continue
            league_name = (data.get("leagues") or [{}])[0].get("name", lg)
            for ev in data.get("events", []):
                n_ev += 1
                ev_obj = _build(sport, ev, league_name, teams, per_team)
                if ev_obj and ev_obj.uid not in found:
                    found[ev_obj.uid] = ev_obj
                    per_team[ev_obj._team] += 1
        log["ligues"][lg] = {"evenements_vus": n_ev, **({"erreur": err} if err else {})}

    log["par_equipe"] = per_team
    return list(found.values())


def _build(sport, ev, league_name, teams, per_team) -> Event | None:
    comp = (ev.get("competitions") or [{}])[0]
    comps = comp.get("competitors") or []
    if len(comps) < 2:
        return None

    ours = None
    for t in teams:
        for c in comps:
            if matches(t["match"], *_all_names(c)):
                ours = (t, c)
                break
        if ours:
            break
    if not ours:
        return None

    home = next((c for c in comps if c.get("homeAway") == "home"), comps[0])
    away = next((c for c in comps if c is not home), comps[1])
    st = (comp.get("status") or ev.get("status") or {}).get("type", {})
    state = st.get("state", "pre")
    name_code = st.get("name", "")
    emoji = EMOJI[sport]

    start = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).astimezone(timezone.utc)

    if "POSTPONED" in name_code:
        state, prefix = "postponed", "[Reporté] "
    elif "CANCEL" in name_code:
        state, prefix = "canceled", "[Annulé] "
    else:
        prefix = ""

    if state == "post":
        hs, as_ = _score(home), _score(away)
        other = away if ours[1] is home else home
        mark = result_mark(_score(ours[1]), _score(other))
        title = f"{emoji} {_name(home)} {hs}–{as_} {_name(away)} {mark}".strip()
    elif state == "in":
        title = f"{emoji} 🔴 {_name(home)} {_score(home)}–{_score(away)} {_name(away)}"
    else:
        title = f"{emoji} {prefix}{_name(home)} – {_name(away)}"

    desc = [f"🏆 {league_name}"]
    if comp.get("timeValid") is False or ev.get("timeValid") is False:
        desc.append("⏰ Horaire à confirmer")
    if st.get("description") and state != "pre":
        desc.append(f"Statut : {st['description']}")
    venue = comp.get("venue") or {}
    loc = ", ".join(x for x in [venue.get("fullName"), (venue.get("address") or {}).get("city")] if x)
    link = next((l.get("href") for l in ev.get("links", []) if l.get("href")), "")

    e = Event(
        uid=f"espn-{sport}-{ev['id']}",
        sport=sport, title=title, start=start, duration_min=DURATION_MIN[sport],
        description="\n".join(desc), location=loc, url=link, state=state,
    )
    e._team = ours[0]["nom"]
    return e
