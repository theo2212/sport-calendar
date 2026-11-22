"""Source Liquipedia (esport) : page « Liquipedia:Matches » de chaque jeu.

Règles de l'API Liquipedia : User-Agent identifiable, gzip, et au plus
1 appel « parse » toutes les 30 s → on attend entre deux jeux.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

from .common import DURATION_MIN, EMOJI, Event, get_json, matches, norm, result_mark

UA = "sport-calendar/1.0 (https://github.com/theo2212/sport-calendar; theo2212@users.noreply.github.com)"
WIKIS = {
    "call of duty": ("callofduty", "CoD"), "cod": ("callofduty", "CoD"),
    "rocket league": ("rocketleague", "RL"), "rl": ("rocketleague", "RL"),
    "valorant": ("valorant", "Valo"), "valo": ("valorant", "Valo"),
    "counter strike": ("counterstrike", "CS2"), "cs2": ("counterstrike", "CS2"),
    "league of legends": ("leagueoflegends", "LoL"), "lol": ("leagueoflegends", "LoL"),
    "fortnite": ("fortnite", "Fortnite"), "dota 2": ("dota2", "Dota"),
    "overwatch": ("overwatch", "OW"), "rainbow six": ("rainbowsix", "R6"),
}
_last_call = [0.0]


def _parse_page(wiki: str) -> str:
    wait = 31 - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    data = get_json(f"https://liquipedia.net/{wiki}/api.php",
                    {"action": "parse", "page": "Liquipedia:Matches", "format": "json", "prop": "text"},
                    headers={"User-Agent": UA, "Accept-Encoding": "gzip"}, retries=1)
    _last_call[0] = time.time()
    return data["parse"]["text"]["*"]


def _cls(*names):
    return lambda c: c and any(n in c.split() for n in names)


def fetch(teams: list[dict], start: datetime, end: datetime, log: dict) -> list[Event]:
    wanted: dict[str, tuple[str, list[dict]]] = {}
    for spec in teams:
        games = spec.get("jeux") or ["call of duty", "rocket league", "valorant"]
        for g in games:
            w = WIKIS.get(norm(g))
            if w:
                wanted.setdefault(w[0], (w[1], []))[1].append(spec)

    found: dict[str, Event] = {}
    log["jeux"] = {}
    now = datetime.now(timezone.utc)
    for wiki, (tag, specs) in wanted.items():
        info = log["jeux"].setdefault(wiki, {})
        try:
            html = _parse_page(wiki)
        except Exception as exc:
            info["erreur"] = str(exc)
            continue
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("div", class_=_cls("match-ticker-card"))
        info["matchs_sur_la_page"] = len(cards)
        n = 0
        for card in cards:
            tobj = card.find(attrs={"data-timestamp": True})
            if not tobj:
                continue
            try:
                st = datetime.fromtimestamp(int(tobj["data-timestamp"]), tz=timezone.utc)
            except ValueError:
                continue
            if not (start <= st <= end):
                continue
            opps = card.find_all("div", class_=_cls("match-ticker-card__opponent"))
            if len(opps) < 2:
                continue
            names, scores = [], []
            for o in opps[:2]:
                nm = o.find(class_=_cls("team-name")) or o.find(class_=_cls("team-bracketname"))
                names.append(nm.get_text(strip=True) if nm else "TBD")
                kids = [d for d in o.find_all("div", recursive=False)]
                sc = kids[-1].get_text(strip=True) if len(kids) > 1 else ""
                scores.append(sc)
            spec = next((s for s in specs if matches(s["match"], *names)), None)
            if not spec:
                continue
            completed = card.find_parent(attrs={"data-toggle-area-content": "2"}) is not None
            has_score = all(re.fullmatch(r"\d+", s or "") for s in scores)
            header = card.find("div", class_=_cls("match-ticker-card__header"))
            fmt = ""
            if header:
                divs = header.find_all("div", recursive=False)
                fmt = divs[-1].get_text(" ", strip=True) if divs else ""
            tour = card.find("div", class_=_cls("match-ticker-card-tournament"))
            tname = ""
            if tour:
                links = [a for a in tour.find_all("a") if a.get_text(strip=True)]
                tname = links[-1].get_text(strip=True) if links else tour.get_text(" ", strip=True)

            emoji = EMOJI["esport"]
            ours_first = matches(spec["match"], names[0])
            if has_score and (completed or st < now - timedelta(hours=4)):
                state = "post"
                mark = result_mark(scores[0] if ours_first else scores[1], scores[1] if ours_first else scores[0])
                title = f"{emoji} [{tag}] {names[0]} {scores[0]}–{scores[1]} {names[1]} {mark}".strip()
            elif has_score and st <= now:
                state = "in"
                title = f"{emoji} 🔴 [{tag}] {names[0]} {scores[0]}–{scores[1]} {names[1]}"
            else:
                state = "pre"
                title = f"{emoji} [{tag}] {names[0]} – {names[1]}"
            uid = f"lq-{wiki}-{int(st.timestamp())}-{norm(names[0])[:12]}-{norm(names[1])[:12]}".replace(" ", "_")
            desc = [x for x in [f"🏆 {tname}" if tname else "", fmt] if x]
            found[uid] = Event(
                uid=uid, sport="esport", title=title, start=st, duration_min=DURATION_MIN["esport"],
                description="\n".join(desc), url=f"https://liquipedia.net/{wiki}/", state=state,
            )
            n += 1
        info["matchs_suivis"] = n
    return list(found.values())
