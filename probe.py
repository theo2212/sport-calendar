import json, re, requests
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
res = {}
h = requests.get("https://biathlonresults.com/", headers={"User-Agent": UA}, timeout=25)
res["home_code"] = h.status_code; res["home"] = h.text[:3000]
scripts = re.findall(r"src=\"?([^ >\"]+\.js)", h.text)
res["scripts"] = scripts
for s in scripts[:6]:
    u = s if s.startswith("http") else "https://biathlonresults.com/" + s.lstrip("/")
    try:
        js = requests.get(u, headers={"User-Agent": UA}, timeout=25).text
        hits = [js[max(0, m.start()-300):m.start()+400] for m in re.finditer(r"sportapi|Authorization|RT=|apikey|api-key|Bearer", js)][:8]
        res[u] = {"len": len(js), "hits": hits}
    except Exception as e:
        res[u] = str(e)
json.dump(res, open("docs/probe2.json", "w"), ensure_ascii=False, indent=1)
