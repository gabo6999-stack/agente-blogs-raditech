"""Tercera tanda: confirma el 301 de los duplicados y el bug de la categoria con '&'."""
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SITES  # noqa: E402
from audit.collect_evidence import wp_headers  # noqa: E402

SITE = "propertyledger"
BASE = SITES[SITE]["wp_url"]
wp_url, headers, _ = wp_headers(SITE)
CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

print("=" * 78)
print("N. Los duplicados del 12-ago: 301 y a donde")
print("=" * 78)
for slug in ["what-is-trust-accounting-property-management",
             "property-management-bookkeeping-vs-accounting",
             "setting-up-property-management-chart-of-accounts",
             "security-deposit-accounting-property-managers-compliance-best-practices-2"]:
    url = f"{BASE}/{slug}/"
    for intento in (1, 2):
        r = requests.get(url, headers={"User-Agent": CHROME}, allow_redirects=False, timeout=30)
        print(f"  intento {intento}: {r.status_code}  /{slug}/"
              + (f"  -> {r.headers.get('location')}" if r.headers.get("location") else ""))
        if r.status_code != 403:
            break
        time.sleep(3)

print()
print("=" * 78)
print("O. BUG DE CATEGORIA: el nombre esta HTML-encoded en la BD")
print("=" * 78)
for q in ["HOA & Condo Accounting", "HOA &amp; Condo Accounting", "Condo Accounting", "HOA"]:
    r = requests.get(f"{wp_url}/wp-json/wp/v2/categories", headers=headers,
                     params={"search": q}, timeout=20)
    got = [(c["id"], c["name"], c["slug"]) for c in r.json()] if r.status_code == 200 else r.text[:100]
    print(f"  search={q!r:<32} -> {got}")
print("\n  -> get_or_create_category busca con el '&' literal, no encuentra nada,")
print("     e intenta CREAR una categoria que ya existe. WordPress responde term_exists")
print("     (no 201), la funcion devuelve None y el post se va a Uncategorized.")

print()
print("=" * 78)
print("P. Estabilidad del edge: 12 peticiones seguidas a la home")
print("=" * 78)
codes = []
for i in range(12):
    t0 = time.time()
    try:
        r = requests.get(BASE + "/", headers={"User-Agent": CHROME, "Cache-Control": "no-cache"},
                         allow_redirects=False, timeout=30)
        codes.append(r.status_code)
        print(f"  {i+1:2d}: {r.status_code}  {(time.time()-t0)*1000:7.0f} ms")
    except Exception as e:
        codes.append("ERR")
        print(f"  {i+1:2d}: ERR  {e}")
    time.sleep(1)
print(f"\n  codigos: {codes}")
print(f"  no-200 : {sum(1 for c in codes if c != 200)}/{len(codes)}")
