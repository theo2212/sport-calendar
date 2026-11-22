"""Diagnostic temporaire : teste les variantes d'API depuis GitHub Actions."""
import json, requests
from curl_cffi import requests as creq
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
E = "https://site.api.espn.com/apis/site/v2/sports"
SOFA_H = {"Referer": "https://www.sofascore.com/", "Origin": "https://www.sofascore.com"}
IBU_H = {"Referer": "https://biathlonresults.com/", "Origin": "https://biathlonresults.com"}
P = [
 ("r", "https://biathlonresults.com/modules/sportapi/api/Events?RT=385698&SeasonId=2627&Level=1", IBU_H),
 ("r", f"{E}/soccer/all/teams/478/schedule", {}),
 ("r", "https://www.thesportsdb.com/api/v1/json/123/searchteams.php?t=Paris%20Saint-Germain%20Handball", {}),
 ("r", "https://www.thesportsdb.com/api/v1/json/123/search_all_leagues.php?s=Handball", {}),
 ("r", "https://www.thesportsdb.com/api/v1/json/123/eventsnext.php?id=133714", {}),
 ("r", "https://www.thesportsdb.com/api/v1/json/123/eventsseason.php?id=4555&s=2026", {}),
 ("r", "https://www.thesportsdb.com/api/v1/json/123/eventsseason.php?id=4554&s=2026-2027", {}),
]
out = []
for kind, url, h in P:
    try:
        if kind == "c":
            r = creq.get(url, headers=h, impersonate="chrome", timeout=25)
        else:
            r = requests.get(url, headers={"User-Agent": UA, "Accept": "application/json", **h}, timeout=25)
        h2 = dict(r.headers)
        out.append({"k": kind, "url": url, "code": r.status_code, "body": r.text[:900], "len": len(r.content), "ctype": r.headers.get("content-type")})
    except Exception as e:
        out.append({"k": kind, "url": url, "err": str(e)[:300]})
import os; os.makedirs("docs", exist_ok=True)
json.dump(out, open("docs/probe.json", "w"), ensure_ascii=False, indent=1)

# Liquipedia : structure de la page des matchs
import re, time
LQH = {"User-Agent": "sport-calendar/1.0 (https://github.com/theo2212/sport-calendar; theo2212@users.noreply.github.com)", "Accept-Encoding": "gzip"}
res = {}
for wiki in ["valorant"]:
    r = requests.get(f"https://liquipedia.net/{wiki}/api.php?action=parse&page=Liquipedia:Matches&format=json&prop=text", headers=LQH, timeout=30)
    html = r.json()["parse"]["text"]["*"]
    i = html.find("data-timestamp")
    res[wiki] = {"len": len(html), "sample": html[max(0,i-3000):i+3000], "n_ts": html.count("data-timestamp"), "gm": [m.start() for m in re.finditer("Gentle", html)][:5]}
    j = html.find("Gentle")
    res[wiki]["gm_sample"] = html[max(0,j-2500):j+1500] if j>=0 else ""
r = requests.get(f"{E}/rugby/270559/scoreboard", timeout=25).json()
res["rugby_cal"] = str((r.get("leagues") or [{}])[0].get("calendar"))[:1500]
json.dump(res, open("docs/probe2.json","w"), ensure_ascii=False, indent=1)
