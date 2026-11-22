import json, re, requests
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
F = "https://fixtures.darts.web.gc.pdcservices.co.uk/v2/"
res = {}
for q in ["participantID=40676", "filter.participantID=40676", "filter[participantID]=40676", "participant=40676",
          "filter.participant1ID=40676", "participantIDs=40676", "filter.startDate.gte=2026-11-01", "sort=-startDate", "page.number=2&page.size=3"]:
    try:
        d = requests.get(F + "?page.size=50&" + q, timeout=20).json()
        rows = d.get("data", [])
        res[q] = {"n": len(rows), "with_littler": sum(1 for r in rows if "40676" in (r["attributes"].get("participant1ID"), r["attributes"].get("participant2ID"))),
                  "dates": sorted({r["attributes"]["startDate"] for r in rows})[:3] + ["…"] + sorted({r["attributes"]["startDate"] for r in rows})[-3:],
                  "meta": d.get("meta"), "links": d.get("links")}
    except Exception as e:
        res[q] = str(e)[:200]
d = requests.get(F + "?page.size=1", timeout=20).json()
res["sample_full"] = json.dumps(d)[:3500]
for p in ["/startlist/BT2627SWRLCP02SMSP", "/startlist/BT2627SWRLCP01SMIN"]:
    r = requests.get("https://www.biathlonworld.com" + p, headers={"User-Agent": UA}, timeout=30)
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    if m:
        pp = json.loads(m.group(1))["props"]["pageProps"]
        res[p] = {"code": r.status_code, "keys": list(pp), "data": {k: json.dumps(v)[:1200] for k, v in pp.items() if k != "_nextI18Next"}}
    else:
        res[p] = r.status_code
html = requests.get("https://www.biathlonworld.com/calendar", headers={"User-Agent": UA}, timeout=30).text
js = re.findall(r'/_next/static/[^"]+\.js', html)
hits = set()
for j in js[:30]:
    t = requests.get("https://www.biathlonworld.com" + j, headers={"User-Agent": UA}, timeout=30).text
    for m in re.finditer(r'https?://[a-zA-Z0-9.\-]*(?:api|biathlon)[a-zA-Z0-9.\-]*[a-zA-Z0-9_/\-]*', t): hits.add(m.group(0))
    for m in re.finditer(r'.{60}Competitions\?.{80}', t): hits.add(m.group(0))
res["bw_js"] = sorted(hits)[:60]
json.dump(res, open("docs/probe.json", "w"), ensure_ascii=False, indent=1)
