"""Outils partagés : HTTP, modèle d'événement, normalisation des noms."""
from __future__ import annotations

import time
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

import requests

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
SESSION = requests.Session()

EMOJI = {
    "foot": "⚽", "basket": "🏀", "rugby": "🏉", "hand": "🤾", "flechettes": "🎯",
    "esport": "🎮", "biathlon": "🎿", "f1": "🏎️", "tennis": "🎾", "volley": "🏐",
    "hockey": "🏒", "cyclisme": "🚴", "baseball": "⚾", "football-us": "🏈",
}
DURATION_MIN = {
    "foot": 120, "basket": 150, "rugby": 120, "hand": 90, "flechettes": 150,
    "esport": 180, "biathlon": 60, "f1": 120, "tennis": 150,
}


class HttpError(RuntimeError):
    pass


def get_json(url: str, params: dict | None = None, headers: dict | None = None,
             retries: int = 2, pause: float = 0.0):
    last = "?"
    for attempt in range(retries + 1):
        try:
            r = SESSION.get(url, params=params, timeout=25,
                            headers={"User-Agent": UA, "Accept": "application/json",
                                     **(headers or {})})
            if r.status_code == 200:
                if pause:
                    time.sleep(pause)
                return r.json()
            last = f"HTTP {r.status_code}"
            if r.status_code in (400, 401, 403, 404):
                break
        except Exception as exc:  # réseau, JSON…
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(2 * (attempt + 1))
    raise HttpError(f"{url} -> {last}")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return " ".join(s.lower().replace("-", " ").split())


def matches(aliases: list[str], *names: str) -> bool:
    """Vrai si un alias apparaît comme mot(s) entier(s) dans un des noms."""
    for n in names:
        nn = f" {norm(n)} "
        for a in aliases:
            if f" {norm(a)} " in nn:
                return True
    return False


@dataclass
class Event:
    uid: str
    sport: str
    title: str
    start: datetime              # UTC
    duration_min: int
    description: str = ""
    location: str = ""
    url: str = ""
    state: str = "pre"           # pre | in | post | postponed | canceled
    all_day: bool = False

    def to_dict(self):
        d = asdict(self)
        d["start"] = self.start.astimezone(timezone.utc).isoformat()
        return d

    @staticmethod
    def from_dict(d):
        d = dict(d)
        d["start"] = datetime.fromisoformat(d["start"])
        return Event(**d)


def result_mark(our_score, their_score) -> str:
    try:
        a, b = float(our_score), float(their_score)
    except (TypeError, ValueError):
        return ""
    return "✅" if a > b else "❌" if a < b else "🤝"


def team_spec(item) -> dict:
    """Normalise une entrée de config (str ou dict)."""
    if isinstance(item, str):
        return {"nom": item, "match": [item]}
    spec = dict(item)
    spec.setdefault("match", [])
    if isinstance(spec["match"], str):
        spec["match"] = [spec["match"]]
    spec["match"] = [spec["nom"], *spec["match"]]
    return spec
