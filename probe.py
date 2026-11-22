"""Diagnostic temporaire : teste les variantes d'API depuis GitHub Actions."""
import json, requests
from curl_cffi import requests as creq
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
E = "https://site.api.espn.com/apis/site/v2/sports"
SOFA_H = {"Referer": "https://www.sofascore.com/", "Origin": "https://www.sofascore.com"}
IBU_H = {"Referer": "https://biathlonresults.com/", "Origin": "https://biathlonresults.com"}
P = [
 ("r", f"{E}/rugby/270559/teams/25912/schedule", {}),
 ("r", f"{E}/rugby/270559/teams/25912/schedule?fixture=true", {}),
 ("r", f"{E}/soccer/uefa.nations/teams/478/schedule?fixture=true", {}),
 ("r", f"{E}/soccer/all/teams/176/schedule?fixture=true", {}),
 ("r", "https://api.sofascore.app/api/v1/sport/darts/scheduled-events/2026-11-22", SOFA_H),
 ("r", "https://api.sofascore.app/api/v1/search/teams?q=Littler", SOFA_H),
 ("r", "https://api.sofascore.app/api/v1/team/2817/events/last/0", SOFA_H),
 ("c", "https://api.sofascore.app/api/v1/sport/handball/scheduled-events/2026-11-22", {}),
 ("r", "https://api.sofascore.app/api/v1/sport/handball/scheduled-events/2026-11-22", {"User-Agent": "SofaScore/24.11.0 (iPhone; iOS 18.0; Scale/3.00)"}),
 ("r", "https://biathlonresults.com/modules/sportapi/api/Events?SeasonId=2627", IBU_H),
 ("r", "https://biathlonresults.com/modules/sportapi/api/Events?SeasonId=2526&Level=1", IBU_H),
 ("r", "https://biathlonresults.com/modules/sportapi/api/Competitions?EventId=BT2627SWRLCP01", IBU_H),
 ("r", "https://biathlonresults.com/modules/sportapi/api/CupResults?CupId=BT2627SWRLCP__SMTS", IBU_H),
 ("r", "https://www.thesportsdb.com/api/v1/json/123/search_all_leagues.php?s=Biathlon", {}),
 ("r", "https://www.thesportsdb.com/api/v1/json/123/searchteams.php?t=Paris%20SG", {}),
 ("r", "https://www.thesportsdb.com/api/v1/json/123/search_all_leagues.php?s=Darts", {}),
 ("r", "https://liquipedia.net/valorant/api.php?action=parse&page=Gentle_Mates&format=json&prop=text", {"User-Agent": "sport-calendar/1.0 (https://github.com/theo2212/sport-calendar; theo2212@users.noreply.github.com)", "Accept-Encoding": "gzip"}),
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
