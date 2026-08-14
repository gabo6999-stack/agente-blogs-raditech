"""Comprobaciones puntuales sobre las hipotesis de la auditoria. Salida literal."""
import json
import os
import re
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SITES  # noqa: E402
from audit.collect_evidence import wp_headers  # noqa: E402

EV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")
SITE = sys.argv[1] if len(sys.argv) > 1 else "propertyledger"

with open(os.path.join(EV, f"{SITE}-posts.json"), encoding="utf-8") as f:
    data = json.load(f)
posts = {p["id"]: p for p in data["posts"]}
wp_url, headers, auth = wp_headers(SITE)

print("=" * 78)
print("A. rank_math_* REALMENTE presentes? (muestra literal de 4 posts)")
print("=" * 78)
for pid in (84, 219, 309, 322):
    p = posts.get(pid)
    if not p:
        continue
    print(f"\n  post #{pid} ({p['author']}, {p['date_gmt'][:10]})")
    for k in ("rank_math_title", "rank_math_description", "rank_math_focus_keyword", "rank_math_seo_score"):
        print(f"    {k:<27} = {p[k]!r}")

print()
print("=" * 78)
print("B. seo_score vs 'lo abrieron en el editor' (modified > date)")
print("=" * 78)
print(f"  {'id':<6}{'score':<7}{'date_gmt':<21}{'modified_gmt':<21}editado_despues")
for p in sorted(data["posts"], key=lambda x: x["date_gmt"] or ""):
    edited = (p["modified_gmt"] or "") > (p["date_gmt"] or "")
    print(f"  {p['id']:<6}{str(p['rank_math_seo_score'] or '-'):<7}{(p['date_gmt'] or '')[:19]:<21}"
          f"{(p['modified_gmt'] or '')[:19]:<21}{edited}")
con = [p for p in data["posts"] if p["rank_math_seo_score"]]
sin = [p for p in data["posts"] if not p["rank_math_seo_score"]]
print(f"\n  CON score : {len(con)} posts, de los cuales {sum(1 for p in con if (p['modified_gmt'] or '') > (p['date_gmt'] or ''))} fueron editados despues de publicar")
print(f"  SIN score : {len(sin)} posts, de los cuales {sum(1 for p in sin if (p['modified_gmt'] or '') > (p['date_gmt'] or ''))} fueron editados despues de publicar")

print()
print("=" * 78)
print("C. Categorias del sitio y prueba literal de get_or_create_category")
print("=" * 78)
print(f"  categorias existentes: {json.dumps(data['categories'], ensure_ascii=False)}")
for name in ["HOA & Condo Accounting", "Trust Accounting", "Financial Reporting",
             "Property Management Accounting"]:
    r = requests.get(f"{wp_url}/wp-json/wp/v2/categories", headers=headers,
                     params={"search": name}, timeout=20)
    try:
        res = r.json()
    except Exception:
        res = r.text[:120]
    got = [(c["id"], c["name"]) for c in res] if isinstance(res, list) else res
    print(f"  search={name!r:<34} HTTP {r.status_code} -> {got}")

print()
print("=" * 78)
print("D. IDs faltantes en la rafaga del 12-ago (312, 317) — que responden hoy")
print("=" * 78)
for pid in (312, 317, 320, 321):
    r = requests.get(f"{wp_url}/wp-json/wp/v2/posts/{pid}", headers=headers,
                     params={"context": "edit"}, timeout=20)
    if r.status_code == 200:
        j = r.json()
        print(f"  #{pid}: HTTP 200  status={j.get('status')}  slug={j.get('slug')}")
    else:
        print(f"  #{pid}: HTTP {r.status_code}  {r.text[:110]}")

print()
print("=" * 78)
print("E. Cuerpo crudo de un post de la rafaga (#309) vs uno del agente (#216)")
print("=" * 78)
for pid in (309, 216):
    r = requests.get(f"{wp_url}/wp-json/wp/v2/posts/{pid}", headers=headers,
                     params={"context": "edit"}, timeout=20)
    raw = r.json()["content"]["raw"]
    print(f"\n  --- post #{pid} — primeros 420 chars del content.raw ---")
    print("  " + raw[:420].replace("\n", "\n  "))
    print(f"  ... [total {len(raw)} chars]")
    print(f"  <h1>: {len(re.findall(r'<h1', raw, re.I))}   <ul>: {len(re.findall(r'<ul', raw, re.I))}"
          f"   <ol>: {len(re.findall(r'<ol', raw, re.I))}   <li>: {len(re.findall(r'<li', raw, re.I))}"
          f"   <h2>: {len(re.findall(r'<h2', raw, re.I))}")

print()
print("=" * 78)
print("F. SALUD DEL SITIO — 5 URLs, sin cache, sin seguir redirecciones")
print("=" * 78)
urls = [SITES[SITE]["wp_url"] + p for p in
        ["/", "/monthly-accounting/", "/hoa-condo-accounting/", "/contact/",
         "/what-is-trust-accounting-property-management-guide/"]]
for ua_name, ua in [("navegador", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/120 Safari/537.36"),
                    ("Googlebot", "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)")]:
    print(f"\n  --- User-Agent: {ua_name} ---")
    for u in urls:
        t0 = time.time()
        try:
            r = requests.get(u, headers={"User-Agent": ua, "Cache-Control": "no-cache",
                                         "Pragma": "no-cache"},
                             allow_redirects=False, timeout=30)
            ms = (time.time() - t0) * 1000
            print(f"    {r.status_code}  {ms:7.0f} ms  {u}"
                  + (f"  -> {r.headers.get('location')}" if r.is_redirect else ""))
        except Exception as e:
            print(f"    ERR {(time.time()-t0)*1000:7.0f} ms  {u}  {e}")

print()
print("=" * 78)
print("G. HTML RENDERIZADO de un post publicado (#309) — H1, canonical, robots, li")
print("=" * 78)
live = posts[309]["link"]
r = requests.get(live, headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"},
                 allow_redirects=False, timeout=30)
print(f"  GET {live}\n  HTTP {r.status_code}  ({len(r.text)} bytes)")
if r.status_code == 200:
    html = r.text
    h1s = [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)]
    print(f"  <h1> en la pagina: {len(h1s)}")
    for h in h1s:
        print(f"    - {h[:100]}")
    can = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', html, re.I)
    print(f"  canonical: {can.group(1) if can else '(no encontrado)'}")
    rob = re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']+)', html, re.I)
    print(f"  robots   : {rob.group(1) if rob else '(no encontrado)'}")
    ttl = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    print(f"  <title>  : {(ttl.group(1).strip() if ttl else '(no encontrado)')[:100]}")
    desc = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)', html, re.I)
    print(f"  meta desc: {(desc.group(1) if desc else '(no encontrado)')[:100]}")

print()
print("=" * 78)
print("H. SITEMAP — esta el post mas reciente?")
print("=" * 78)
for sm in ["/sitemap_index.xml", "/post-sitemap.xml"]:
    r = requests.get(SITES[SITE]["wp_url"] + sm, headers={"User-Agent": "Mozilla/5.0"},
                     allow_redirects=False, timeout=30)
    print(f"  GET {sm} -> HTTP {r.status_code} ({len(r.text)} bytes)")
    if r.status_code == 200 and "post-sitemap" in r.text:
        print("    contiene post-sitemap: si")
    if r.status_code == 200 and sm == "/post-sitemap.xml":
        for pid in (322, 309):
            print(f"    post #{pid} ({posts[pid]['slug']}) en el sitemap: "
                  f"{posts[pid]['slug'] in r.text}")
