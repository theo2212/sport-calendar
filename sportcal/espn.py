"""Source ESPN (API publique du site) : foot, basket, rugby.

- foot / basket : on retrouve l'identifiant ESPN de l'équipe par son nom,
  puis on lit son calendrier (toutes compétitions) + ses résultats.
- rugby : le calendrier par équipe n'existe pas chez ESPN → on parcourt les
  journées (vendredi→dimanche + dates connues) des compétitions suivies.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from .common import DURATION_MIN, EMOJI, Event, get_json, matches, result_mark

BASE = "https://site.api.espn.com/apis/site/v2/sports"
SPORT_PATH = {"foot": "soccer", "basket": "basketball", "rugby": "rugby"}

# Où chercher l'équipe (foot/basket)
LOOKUP_LEAGUES = {
    "foot": ["fra.1", "fra.2", "eng.1", "esp.1", "ita.1", "ger.1", "uefa.champions",
             "uefa.nations", "fifa.world", "fifa.friendly"],
    "basket": ["nba", "wnba"],
}
# Compétitions parcourues pour le rugby
RUGBY_LEAGUES = {
    "270559": "Top 14", "271937": "Champions Cup", "272073": "Challenge Cup",
    "180659": "Tournoi des Six Nations", "289234": "Test-match", "164205": "Coupe du monde",
}


def fetch(sport: str, teams: list[dict], start: datetime, end: datetime, log: dict) -> list[Event]:
    if sport == "rugby":
        return _fetch_scan(sport, teams, start, end, log)
    return _fetch_schedule(sport, teams, start, end, log)


# ── foot / basket ────────────────────────────────────────────────────────────
def _resolve(sport, spec, cache):
    path = SPORT_PATH[sport]
    leagues = [str(x) for x in (spec.get("ligues") or [])] + LOOKUP_LEAGUES[sport]
    for lg in leagues:
        if lg not in cache:
            try:
                data = get_json(f"{BASE}/{path}/{lg}/teams", retries=1)
                cache[lg] = [t["team"] for t in data["sports"][0]["leagues"][0]["teams"]]
            except Exception:
                cache[lg] = []
        exact = [t for t in cache[lg] if t.get("displayName", "").lower() == spec["nom"].lower()]
        cands = exact or [t for t in cache[lg] if matches(
            spec["match"], t.get("displayName", ""), t.get("shortDisplayName", ""),
            t.get("name", ""), t.get("location", ""))]
        if cands:
            return cands[0], lg
    return None, None


def _fetch_schedule(sport, teams, start, end, log):
    path = SPORT_PATH[sport]
    found: dict[str, Event] = {}
    cache: dict = {}
    log["par_equipe"] = {}
    for spec in teams:
        info = log["par_equipe"].setdefault(spec["nom"], {})
        if spec.get("espn_id"):
            team, lg = {"id": spec["espn_id"], "displayName": spec["nom"]}, spec.get("ligue", "all")
        else:
            team, lg = _resolve(sport, spec, cache)
        if not team:
            info["erreur"] = "équipe introuvable chez ESPN"
            info["matchs"] = 0
            continue
        info["trouve"] = f"{team.get('displayName')} (id {team['id']}, {lg})"
        lg_path = "all" if sport == "foot" else lg
        base = f"{BASE}/{path}/{lg_path}/teams/{team['id']}/schedule"
        urls = [base, base + ("?fixture=true" if sport == "foot" else "?seasontype=3")]
        n = 0
        for u in urls:
            try:
                data = get_json(u, retries=1)
            except Exception as exc:
                if "seasontype" not in u:
                    info.setdefault("avertissements", []).append(str(exc))
                continue
            for ev in data.get("events", []):
                lname = (ev.get("league") or {}).get("name") or (ev.get("seasonType") or {}).get("name", "")
                e = _build(sport, ev, lname, [spec], start, end)
                if e and e.uid not in found:
                    found[e.uid] = e
                    n += 1
        info["matchs"] = n
    return list(found.values())


# ── rugby ────────────────────────────────────────────────────────────────────
def _fetch_scan(sport, teams, start, end, log):
    path = SPORT_PATH[sport]
    leagues = dict(RUGBY_LEAGUES)
    for t in teams:
        for lg in t.get("ligues", []) or []:
            leagues.setdefault(str(lg), str(lg))

    days, d = set(), start.date()
    while d <= end.date():
        if d.weekday() >= 4:          # ven, sam, dim
            days.add(d)
        d += timedelta(days=1)

    jobs = []
    for lg in leagues:
        extra = set()
        try:
            cal = (get_json(f"{BASE}/{path}/{lg}/scoreboard", retries=1).get("leagues") or [{}])[0].get("calendar") or []
            for c in cal:
                s = c if isinstance(c, str) else c.get("startDate", "")
                if s:
                    dd = datetime.fromisoformat(s.replace("Z", "+00:00")).date()
                    if start.date() <= dd <= end.date():
                        extra.add(dd)
        except Exception:
            pass
        jobs += [(lg, dd) for dd in sorted(days | extra)]

    def one(job):
        lg, dd = job
        try:
            return lg, get_json(f"{BASE}/{path}/{lg}/scoreboard", {"dates": f"{dd:%Y%m%d}"}, retries=1)
        except Exception as exc:
            return lg, exc

    found: dict[str, Event] = {}
    per_team = {t["nom"]: 0 for t in teams}
    stats = {lg: {"requetes": 0, "erreurs": 0, "matchs_vus": 0} for lg in leagues}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for lg, data in pool.map(one, jobs):
            stats[lg]["requetes"] += 1
            if isinstance(data, Exception):
                stats[lg]["erreurs"] += 1
                stats[lg]["derniere_erreur"] = str(data)[:200]
                continue
            for ev in data.get("events", []):
                stats[lg]["matchs_vus"] += 1
                e = _build(sport, ev, leagues[lg], teams, start, end)
                if e and e.uid not in found:
                    found[e.uid] = e
                    per_team[e._team] += 1
    log["ligues"] = stats
    log["par_equipe"] = {k: {"matchs": v} for k, v in per_team.items()}
    return list(found.values())


# ── construction d'un événement ──────────────────────────────────────────────
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
    return [t.get(k, "") or "" for k in ("displayName", "shortDisplayName", "name", "location", "nickname")]


def _build(sport, ev, league_name, teams, start_w, end_w) -> Event | None:
    try:
        start = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None
    if not (start_w <= start <= end_w):
        return None
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
    code = st.get("name", "")
    emoji = EMOJI[sport]

    prefix = ""
    if "POSTPONED" in code:
        state, prefix = "postponed", "[Reporté] "
    elif "CANCEL" in code:
        state, prefix = "canceled", "[Annulé] "

    if state == "post":
        other = away if ours[1] is home else home
        mark = result_mark(_score(ours[1]), _score(other))
        title = f"{emoji} {_name(home)} {_score(home)}–{_score(away)} {_name(away)} {mark}".strip()
    elif state == "in":
        title = f"{emoji} 🔴 {_name(home)} {_score(home)}–{_score(away)} {_name(away)}"
    else:
        title = f"{emoji} {prefix}{_name(home)} – {_name(away)}"

    desc = [f"🏆 {league_name}"] if league_name else []
    if comp.get("timeValid") is False or ev.get("timeValid") is False:
        desc.append("⏰ Horaire à confirmer")
    if st.get("description") and state != "pre":
        desc.append(f"Statut : {st['description']}")
    venue = comp.get("venue") or {}
    loc = ", ".join(x for x in [venue.get("fullName"), (venue.get("address") or {}).get("city")] if x)
    link = next((l.get("href") for l in ev.get("links", []) if l.get("href")), "")

    e = Event(
        uid=f"espn-{sport}-{ev['id']}", sport=sport, title=title, start=start,
        duration_min=DURATION_MIN[sport], description="\n".join(desc), location=loc,
        url=link, state=state,
    )
    e._team = ours[0]["nom"]
    return e
