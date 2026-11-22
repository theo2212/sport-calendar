import json, re, requests
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
H = {"User-Agent": UA, "Accept": "application/json", "Origin": "https://www.pdc.tv", "Referer": "https://www.pdc.tv/"}
res = {}
def nd(url):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    if not m: return {"code": r.status_code}
    pp = json.loads(m.group(1))["props"]["pageProps"]
    c = pp.get("competitionsInitialState")
    return {"code": r.status_code, "page": json.loads(m.group(1)).get("page"), "keys": list(pp), "n_comp": len(c) if isinstance(c, list) else None, "first": (c or [{}])[0].get("RaceId") if isinstance(c, list) else str(c)[:300], "other": {k: json.dumps(v)[:800] for k, v in pp.items() if k not in ("_nextI18Next", "initialContentfulVenues", "seasonInitialState", "eventInitialState", "cupContainerInitialState")}}
for u in ["https://www.biathlonworld.com/calendar?eventId=BT2627SWRLCP02",
          "https://www.biathlonworld.com/calendar/BT2627SWRLCP02",
          "https://www.biathlonworld.com/_next/data/build/calendar.json?eventId=BT2627SWRLCP02",
          "https://www.biathlonworld.com/results",
          "https://www.biathlonworld.com/results?raceId=BT2526SWRLCP01SMIN"]:
    try: res[u] = nd(u) if "_next" not in u else requests.get(u, headers={"User-Agent": UA}, timeout=30).text[:1500]
    except Exception as e: res[u] = str(e)
html = requests.get("https://www.biathlonworld.com/calendar", headers={"User-Agent": UA}, timeout=30).text
res["bw_links"] = sorted(set(re.findall(r'href="(/[a-z\-]+[^"]{0,80})"', html)))[:80]
for u in ["https://participants.darts.web.gc.pdcservices.co.uk/v2/?page.size=5",
          "https://participants.darts.web.gc.pdcservices.co.uk/v2/?search=Littler",
          "https://matches.darts.web.gc.pdcservices.co.uk/v2/?page.size=5",
          "https://matches.darts.web.gc.pdcservices.co.uk/v2/matches?page.size=5",
          "https://matches.darts.web.gc.pdcservices.co.uk/v2/fixtures?page.size=5",
          "https://matches.darts.web.gc.pdcservices.co.uk/v2/tournaments?page.size=5",
          "https://cms.gc.pdcservices.co.uk/v2/tournaments"]:
    try:
        r = requests.get(u, headers=H, timeout=30); res[u] = {"code": r.status_code, "body": r.text[:2500]}
    except Exception as e: res[u] = str(e)
# chercher les routes API dans le JS de pdc.tv
p = requests.get("https://www.pdc.tv/fixtures-results", headers={"User-Agent": UA}, timeout=30).text
js = re.findall(r'/_nuxt/[A-Za-z0-9_\-]+\.js', p)
hits = set()
for j in list(dict.fromkeys(js))[:25]:
    try:
        t = requests.get("https://www.pdc.tv" + j, headers={"User-Agent": UA}, timeout=30).text
        for m in re.finditer(r'["`/](v2/[a-zA-Z0-9_\-/${}.?=&]{3,80})', t): hits.add(m.group(1))
        for m in re.finditer(r'(matchesWeb|matchesUrl|participantsWeb|darts\.web)[^,;]{0,160}', t): hits.add(m.group(0))
    except Exception: pass
res["pdc_js_routes"] = sorted(hits)[:120]
json.dump(res, open("docs/probe.json", "w"), ensure_ascii=False, indent=1)
