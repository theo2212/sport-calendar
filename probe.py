import json, socket, requests, sys
sys.path.insert(0, ".")
from sportcal import biathlon
res = {}
for sub in ["matches", "fixtures", "schedules", "schedule", "events", "tournaments", "results", "competitions", "stats", "draws", "match", "scores", "livescores", "orderofplay"]:
    host = f"{sub}.darts.web.gc.pdcservices.co.uk"
    try:
        socket.gethostbyname(host); ok = True
    except Exception:
        ok = False
    if ok:
        for path in ["/v2/?page.size=3", "/v2/"]:
            try:
                r = requests.get(f"https://{host}{path}", timeout=20, headers={"Accept": "application/json"})
                res[host + path] = {"code": r.status_code, "body": r.text[:1500]}
            except Exception as e:
                res[host + path] = str(e)[:200]
    else:
        res[host] = "pas de DNS"
res["podium_test"] = biathlon._podium("BT2526SWRLCP09SMMS")
json.dump(res, open("docs/probe.json", "w"), ensure_ascii=False, indent=1)
