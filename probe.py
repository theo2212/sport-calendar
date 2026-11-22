"""Diagnostic temporaire : teste les variantes d'API depuis GitHub Actions."""
import json, requests
from curl_cffi import requests as creq
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
E = "https://site.api.espn.com/apis/site/v2/sports"
SOFA_H = {"Referer": "https://www.sofascore.com/", "Origin": "https://www.sofascore.com"}
IBU_H = {"Referer": "https://biathlonresults.com/", "Origin": "https://biathlonresults.com"}
P = [
 ("r", f"{E}/soccer/fra.1/scoreboard?dates=20261122", {}),
 ("r", f"{E}/soccer/fra.1/scoreboard?dates=20261101-20261130", {}),
 ("r", f"{E}/soccer/fra.1/scoreboard?dates=20261101-20261130&limit=100", {}),
 ("r", f"{E}/soccer/fra.1/teams", {}),
 ("r", f"{E}/soccer/fra.1/teams/176/schedule", {}),
 ("r", f"{E}/soccer/fra.1/teams/176/schedule?fixture=true", {}),
 ("r", f"{E}/basketball/nba/scoreboard?dates=20261101-20261130", {}),
 ("r", f"{E}/basketball/nba/teams/sa/schedule", {}),
 ("r", f"{E}/rugby/270559/scoreboard", {}),
 ("r", f"{E}/rugby/270559/scoreboard?dates=20261122", {}),
 ("r", f"{E}/rugby/270559/teams", {}),
 ("r", f"{E}/soccer/uefa.nations/teams", {}),
 ("r", "https://api.sofascore.app/api/v1/search/all?q=Littler&page=0", SOFA_H),
 ("c", "https://api.sofascore.app/api/v1/search/all?q=Littler&page=0", SOFA_H),
 ("c", "https://www.sofascore.com/api/v1/search/all?q=Littler&page=0", SOFA_H),
 ("c", "https://api.sofascore.com/api/v1/search/all?q=Littler&page=0", SOFA_H),
 ("r", "https://biathlonresults.com/modules/sportapi/api/Events?SeasonId=2627&Level=1", IBU_H),
 ("c", "https://biathlonresults.com/modules/sportapi/api/Events?SeasonId=2627&Level=1", IBU_H),
 ("r", "https://biathlonresults.com/modules/sportapi/api/Seasons", IBU_H),
 ("r", "https://www.thesportsdb.com/api/v1/json/123/searchteams.php?t=Paris%20Saint-Germain", {}),
 ("r", "https://www.thesportsdb.com/api/v1/json/123/searchplayers.php?p=Luke%20Littler", {}),
 ("r", "https://liquipedia.net/valorant/api.php?action=parse&page=Gentle_Mates&format=json&prop=text", {"Accept-Encoding": "gzip"}),
 ("r", "https://api.pandascore.co/teams?search[name]=Gentle", {}),
]
out = []
for kind, url, h in P:
    try:
        if kind == "c":
            r = creq.get(url, headers=h, impersonate="chrome", timeout=25)
        else:
            r = requests.get(url, headers={"User-Agent": UA, "Accept": "application/json", **h}, timeout=25)
        out.append({"k": kind, "url": url, "code": r.status_code, "body": r.text[:900]})
    except Exception as e:
        out.append({"k": kind, "url": url, "err": str(e)[:300]})
import os; os.makedirs("docs", exist_ok=True)
json.dump(out, open("docs/probe.json", "w"), ensure_ascii=False, indent=1)
