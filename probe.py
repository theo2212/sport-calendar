import json, re, requests
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
res = {}
html = requests.get("https://www.biathlonworld.com/calendar", headers={"User-Agent": UA}, timeout=30).text
nd = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S).group(1))
pp = nd["props"]["pageProps"]
res["bw_keys"] = list(pp.keys())
res["bw_buildId"] = nd.get("buildId")
res["bw_query"] = nd.get("query"); res["bw_page"] = nd.get("page")
for k, v in pp.items():
    if k != "_nextI18Next":
        res["bw_" + k] = json.dumps(v, ensure_ascii=False)[:4000]
p = requests.get("https://www.pdc.tv/tournaments", headers={"User-Agent": UA}, timeout=30).text
res["pdc_urls"] = sorted(set(re.findall(r'https?://[a-zA-Z0-9.\-]+pdcservices[^"\'\s<>]*', p)))[:40]
res["pdc_nuxt"] = [p[m.start():m.start()+2500] for m in re.finditer(r'__NUXT_DATA__|window.__NUXT__', p)][:2]
for u in ["https://www.pdc.tv/tournaments/_payload.json", "https://www.pdc.tv/fixtures-results", "https://www.pdc.tv/players/luke-littler"]:
    try:
        r = requests.get(u, headers={"User-Agent": UA}, timeout=30)
        res[u] = {"code": r.status_code, "len": len(r.text), "urls": sorted(set(re.findall(r'https?://[a-zA-Z0-9.\-]+pdcservices[^"\'\s<>]*', r.text)))[:30], "head": r.text[:300]}
    except Exception as e:
        res[u] = str(e)
json.dump(res, open("docs/probe.json", "w"), ensure_ascii=False, indent=1)
