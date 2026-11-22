"""Génère docs/*.ics à partir de config.yaml.

Lancé toutes les 2 h par GitHub Actions. Si une source tombe en panne,
on garde les derniers matchs connus pour ce sport (le calendrier ne se vide
jamais d'un coup).
"""
from __future__ import annotations

import hashlib
import json
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from sportcal import biathlon, espn, f1, ics, sofascore
from sportcal.common import Event, team_spec

ROOT = Path(__file__).parent
OUT = ROOT / "docs"
STATE = OUT / "events.json"

NOMS = {
    "foot": "Foot", "basket": "Basket", "rugby": "Rugby", "hand": "Hand",
    "flechettes": "Fléchettes", "esport": "Esport", "biathlon": "Biathlon", "f1": "F1",
}
COULEURS = {
    "foot": "#2E7D32", "basket": "#E65100", "rugby": "#6A1B9A", "hand": "#1565C0",
    "flechettes": "#C62828", "esport": "#00ACC1", "biathlon": "#546E7A", "f1": "#D50000",
}
OFF = {"non", "no", "off", "false", "aucun", ""}


def _enabled(v) -> bool:
    return v is not None and v is not False and str(v).strip().lower() not in OFF


def collect(cfg: dict, start, end, status: dict) -> dict[str, list[Event] | None]:
    """Retourne {sport: [Event]} ; None si la source a échoué."""
    res: dict[str, list[Event] | None] = {}
    for sport, val in cfg.items():
        if sport == "reglages":
            continue
        log = status.setdefault(sport, {})
        try:
            if sport == "biathlon":
                res[sport] = biathlon.fetch(start, end, log) if _enabled(val) else []
            elif sport == "f1":
                res[sport] = f1.fetch(start, end, log) if _enabled(val) else []
            else:
                teams = [team_spec(x) for x in (val or [])]
                if sport in espn.SPORT_PATH:
                    evs = espn.fetch(sport, teams, start, end, log)
                    # Équipe sans aucun match chez ESPN → on tente Sofascore
                    missing = [t for t in teams if log.get("par_equipe", {}).get(t["nom"], 0) == 0]
                    if missing:
                        log["repli_sofascore"] = {}
                        evs += sofascore.fetch(sport, missing, start, end, log["repli_sofascore"])
                else:
                    evs = sofascore.fetch(sport, teams, start, end, log)
                res[sport] = evs
            log["ok"] = True
            log["nb_evenements"] = len(res[sport])
        except Exception as exc:
            log["ok"] = False
            log["erreur"] = f"{type(exc).__name__}: {exc}"
            log["trace"] = traceback.format_exc()[-1500:]
            res[sport] = None
    return res


def main() -> int:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8")) or {}
    reg = cfg.get("reglages") or {}
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=int(reg.get("jours_passes", 30)))
    end = now + timedelta(days=int(reg.get("jours_futurs", 180)))

    prev = json.loads(STATE.read_text()) if STATE.exists() else {}
    status: dict = {}
    fresh = collect(cfg, start, end, status)

    new_state: dict = {}
    for sport, evs in fresh.items():
        if evs is None:  # source en panne → on garde l'existant
            for uid, it in prev.items():
                if it["sport"] == sport:
                    new_state[uid] = it
            continue
        for e in evs:
            d = e.to_dict()
            h = hashlib.sha1(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            old = prev.get(e.uid)
            if old and old["hash"] == h:
                seq, mod = old["seq"], old["modified"]
            else:
                seq = (old["seq"] + 1) if old else 0
                mod = now.isoformat()
            new_state[e.uid] = {"sport": sport, "hash": h, "seq": seq, "modified": mod, "event": d}

    OUT.mkdir(exist_ok=True)
    items_by_sport: dict[str, list] = {}
    for it in new_state.values():
        items_by_sport.setdefault(it["sport"], []).append({
            "event": Event.from_dict(it["event"]), "seq": it["seq"],
            "modified": datetime.fromisoformat(it["modified"]),
        })

    all_items = [x for v in items_by_sport.values() for x in v]
    (OUT / "calendar.ics").write_text(ics.build("Mes sports", all_items), encoding="utf-8", newline="")
    for old in OUT.glob("sport-*.ics"):
        old.unlink()
    for sport, items in items_by_sport.items():
        nom = NOMS.get(sport, sport.capitalize())
        (OUT / f"sport-{sport}.ics").write_text(
            ics.build(nom, items, COULEURS.get(sport, "")), encoding="utf-8", newline="")

    STATE.write_text(json.dumps(new_state, ensure_ascii=False, indent=1, sort_keys=True))
    status["_resume"] = {
        "genere_le": now.isoformat(), "total": len(all_items),
        "par_sport": {k: len(v) for k, v in items_by_sport.items()},
        "sources_en_panne": [k for k, v in fresh.items() if v is None],
    }
    (OUT / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=1))
    print(json.dumps(status["_resume"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
