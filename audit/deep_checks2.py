"""Segunda tanda: WAF/User-Agent, capacidades del usuario, robots.txt, enlaces internos."""
import json
import os
import re
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SITES  # noqa: E402
from audit.collect_evidence import wp_headers  # noqa: E402

SITE = sys.argv[1] if len(sys.argv) > 1 else "propertyledger"
BASE = SITES[SITE]["wp_url"]
wp_url, headers, auth = wp_headers(SITE)

CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
GBOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
GBOT_SMART = ("Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; "
              "+http://www.google.com/bot.html) Chrome/120.0.0.0 Safari/537.36")

print("=" * 78)
print("I. EL 403 ES POR USER-AGENT? mismo URL, distintos UA")
print("=" * 78)
target = f"{BASE}/what-is-trust-accounting-property-management/"
for name, ua in [("(sin UA / python-requests)", None), ("Mozilla/5.0 (corto)", "Mozilla/5.0"),
                 ("Chrome completo", CHROME), ("Googlebot clasico", GBOT),
                 ("Googlebot smartphone-ish", GBOT_SMART), ("curl/8.4.0", "curl/8.4.0")]:
    h = {"Cache-Control": "no-cache"}
    if ua:
        h["User-Agent"] = ua
    t0 = time.time()
    try:
        r = requests.get(target, headers=h, allow_redirects=False, timeout=30)
        print(f"  {r.status_code}  {(time.time()-t0)*1000:7.0f} ms  {name:<28} ({len(r.text)} bytes)")
        if r.status_code == 403:
            print(f"        cuerpo: {r.text.strip()[:150]!r}")
            print(f"        server: {r.headers.get('server')} | {dict(list(r.headers.items())[:6])}")
    except Exception as e:
        print(f"  ERR  {name}: {e}")

print()
print("=" * 78)
print("J. Lo mismo sobre sitemap y robots.txt")
print("=" * 78)
for path in ["/robots.txt", "/sitemap_index.xml", "/post-sitemap.xml", "/wp-sitemap.xml"]:
    for name, ua in [("Chrome", CHROME), ("Googlebot", GBOT)]:
        r = requests.get(BASE + path, headers={"User-Agent": ua}, allow_redirects=False, timeout=30)
        print(f"  {r.status_code}  {path:<22} [{name}]  {len(r.text)} bytes"
              + (f" -> {r.headers.get('location')}" if r.is_redirect else ""))
    if path == "/robots.txt":
        r = requests.get(BASE + path, headers={"User-Agent": CHROME}, timeout=30)
        if r.status_code == 200:
            print("  --- robots.txt ---")
            for line in r.text.strip().splitlines()[:25]:
                print(f"    {line}")

print()
print("=" * 78)
print("K. Capacidades del usuario publicador (por que falla crear categoria)")
print("=" * 78)
r = requests.get(f"{wp_url}/wp-json/wp/v2/users/me", headers=headers,
                 params={"context": "edit"}, timeout=20)
if r.status_code == 200:
    me = r.json()
    print(f"  usuario: {me.get('slug')} (id {me.get('id')})  roles={me.get('roles')}")
    caps = me.get("capabilities", {})
    for c in ["manage_categories", "manage_terms", "edit_posts", "publish_posts",
              "unfiltered_html", "edit_others_posts", "upload_files"]:
        print(f"    {c:<20} = {caps.get(c, False)}")
else:
    print(f"  HTTP {r.status_code}: {r.text[:200]}")

print()
print("=" * 78)
print("L. ENLACES INTERNOS de config.py — verificados SIN seguir redirecciones")
print("=" * 78)
for url, desc in SITES[SITE]["prompt_profile"]["internal_links"].items():
    t0 = time.time()
    try:
        r = requests.get(url, headers={"User-Agent": CHROME, "Cache-Control": "no-cache"},
                         allow_redirects=False, timeout=30)
        loc = f"  -> {r.headers.get('location')}" if r.is_redirect else ""
        flag = "" if r.status_code == 200 else "   <-- ROTO / REDIRIGE"
        print(f"  {r.status_code}  {(time.time()-t0)*1000:6.0f} ms  {url}{loc}{flag}")
    except Exception as e:
        print(f"  ERR  {url}  {e}")

print()
print("=" * 78)
print("M. Enlaces internos REALES dentro de los articulos publicados")
print("=" * 78)
EV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")
with open(os.path.join(EV, f"{SITE}-posts.json"), encoding="utf-8") as f:
    posts = json.load(f)["posts"]
checked = {}
host = BASE.replace("https://", "")
for p in sorted(posts, key=lambda x: x["date_gmt"] or "")[-6:]:
    r = requests.get(f"{wp_url}/wp-json/wp/v2/posts/{p['id']}", headers=headers,
                     params={"context": "edit"}, timeout=20)
    raw = r.json()["content"]["raw"]
    links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', raw, re.I | re.S)
    internal = [(u, re.sub(r"<[^>]+>", "", a).strip()) for u, a in links if host in u]
    external = [u for u, _ in links if host not in u and u.startswith("http")]
    print(f"\n  #{p['id']} {p['slug'][:52]}")
    print(f"      internos={len(internal)}  externos={len(external)}")
    for u, anchor in internal:
        if u not in checked:
            try:
                rr = requests.get(u, headers={"User-Agent": CHROME}, allow_redirects=False, timeout=25)
                checked[u] = (rr.status_code, rr.headers.get("location"))
            except Exception as e:
                checked[u] = ("ERR", str(e)[:40])
        code, loc = checked[u]
        mark = "" if code == 200 else f"   <-- {code}" + (f" -> {loc}" if loc else "")
        print(f"      [{code}] {u[:72]}  |  {anchor[:34]!r}{mark}")
