import json, re, time, requests
T = "https://www.thesportsdb.com/api/v1/json/123"
LQH = {"User-Agent": "sport-calendar/1.0 (https://github.com/theo2212/sport-calendar; theo2212@users.noreply.github.com)", "Accept-Encoding": "gzip"}
res = {}
g = lambda u: requests.get(u, timeout=25).json()
L = g(f"{T}/search_all_leagues.php?s=Handball")["countries"]
res["hand_leagues"] = [(x["idLeague"], x["strLeague"], x["strCountry"], x.get("strCurrentSeason")) for x in L]
for lid, name, c, s in res["hand_leagues"]:
    if c in ("France", "World") or "EHF" in name or "Champions" in name or "International" in name or "Euro" in name:
        try:
            teams = g(f"{T}/lookup_all_teams.php?id={lid}").get("teams") or []
            res[f"teams_{lid}_{name}"] = [(t["idTeam"], t["strTeam"]) for t in teams][:40]
        except Exception as e:
            res[f"teams_{lid}"] = str(e)
for q in ["Paris SG Handball", "PSG Handball", "France Handball", "Paris Saint Germain HB", "France"]:
    try:
        res[f"search_{q}"] = [(t["idTeam"], t["strTeam"], t["strSport"]) for t in (g(f"{T}/searchteams.php?t={q}").get("teams") or [])]
    except Exception as e:
        res[f"search_{q}"] = str(e)
for u in [f"{T}/eventsnext.php?id=136716", f"{T}/eventslast.php?id=136716", f"{T}/searchevents.php?e=Littler", f"{T}/searchevents.php?e=Luke_Littler"]:
    try: res[u] = str(g(u))[:1500]
    except Exception as e: res[u] = str(e)
for wiki in ["rocketleague", "callofduty", "valorant"]:
    time.sleep(31)
    try:
        r = requests.get(f"https://liquipedia.net/{wiki}/api.php?action=parse&page=Liquipedia:Matches&format=json&prop=text", headers=LQH, timeout=30)
        html = r.json()["parse"]["text"]["*"]
        names = sorted(set(re.findall(r'class="team-name">([^<]+)<', html)))
        res[f"lq_{wiki}"] = {"code": r.status_code, "cards": html.count("match-ticker-card__header") + html.count("match-ticker-card&#95;&#95;header"), "gentle": [n for n in names if "entle" in n], "n_names": len(names)}
    except Exception as e:
        res[f"lq_{wiki}"] = str(e)
json.dump(res, open("docs/probe2.json", "w"), ensure_ascii=False, indent=1)
