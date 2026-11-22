import json, re, requests
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
T = "https://www.thesportsdb.com/api/v1/json/123"
P = [
 ("https://www.biathlonworld.com/calendar", {}),
 ("https://www.biathlonworld.com/calendar/season-2026-2027", {}),
 ("https://en.wikipedia.org/w/api.php?action=parse&page=2026%E2%80%9327_Biathlon_World_Cup&prop=wikitext&format=json&section=1", {}),
 ("https://biathlonresults.com/modules/sportapi/api/Events?SeasonId=2627&Level=1", {"Referer": "https://biathlonresults.com/", "Origin": "https://biathlonresults.com", "X-Requested-With": "XMLHttpRequest"}),
 ("https://api.biathlonresults.com/modules/sportapi/api/Events?SeasonId=2627&Level=1", {}),
 (f"{T}/eventsnext.php?id=136716", {}),
 (f"{T}/eventslast.php?id=136716", {}),
 (f"{T}/search_all_leagues.php?s=Darts", {}),
 ("https://www.flashscore.com/player/littler-luke/", {}),
 ("https://www.pdc.tv/tournaments", {}),
 ("https://www.dartsdatabase.co.uk/PlayerDetails.aspx?playerKey=41296", {}),
]
out = []
for url, h in P:
    try:
        r = requests.get(url, headers={"User-Agent": UA, **h}, timeout=25)
        body = r.text
        nd = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.{0,1500})', body)
        out.append({"url": url, "code": r.status_code, "len": len(body), "ctype": r.headers.get("content-type"),
                    "body": body[:1500], "next": nd.group(1) if nd else None,
                    "api_hits": list(set(re.findall(r'https?://[a-zA-Z0-9.\-]+/[a-zA-Z0-9_\-/]*api[a-zA-Z0-9_\-/]*', body)))[:20]})
    except Exception as e:
        out.append({"url": url, "err": str(e)[:300]})
json.dump(out, open("docs/probe.json", "w"), ensure_ascii=False, indent=1)
