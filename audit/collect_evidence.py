"""Recolector de evidencia cruda para la auditoria del agente de blogs.

No infiere nada: baja los posts vía REST con context=edit y vuelca a JSON los
campos que las 10 compuertas necesitan (autor, fecha, slug, categorias, meta de
Rank Math, H1 en el cuerpo, <li> huerfanos). Uso:

    python audit/collect_evidence.py propertyledger
"""
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SITES  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")


def wp_headers(site_key):
    site = SITES[site_key]
    r = requests.post(
        f"{site['wp_url']}/wp-json/jwt-auth/v1/token",
        json={"username": site["wp_user"], "password": site["wp_password"]},
        timeout=20,
    )
    if r.status_code == 200 and r.json().get("token"):
        return site["wp_url"], {"Authorization": f"Bearer {r.json()['token']}",
                                "Content-Type": "application/json"}, "jwt"
    import base64
    cred = base64.b64encode(f"{site['wp_user']}:{site['wp_password']}".encode()).decode()
    return site["wp_url"], {"Authorization": f"Basic {cred}",
                            "Content-Type": "application/json"}, f"basic (jwt {r.status_code})"


def fetch_all(wp_url, headers, endpoint, params):
    out, page = [], 1
    while True:
        p = dict(params, page=page, per_page=100)
        r = requests.get(f"{wp_url}/wp-json/wp/v2/{endpoint}", headers=headers, params=p, timeout=40)
        if r.status_code != 200:
            print(f"  ! {endpoint} page {page} -> HTTP {r.status_code}: {r.text[:200]}")
            break
        batch = r.json()
        if not batch:
            break
        out.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return out


def orphan_li(html):
    """Cuenta <li> que no estan dentro de un <ul>/<ol> abierto."""
    depth, orphans = 0, 0
    for tag in re.findall(r"<\s*(/?)\s*(ul|ol|li)\b[^>]*>", html or "", re.I):
        closing, name = tag[0] == "/", tag[1].lower()
        if name in ("ul", "ol"):
            depth += -1 if closing else 1
            depth = max(depth, 0)
        elif name == "li" and not closing and depth == 0:
            orphans += 1
    return orphans


def main(site_key):
    os.makedirs(OUT_DIR, exist_ok=True)
    wp_url, headers, auth_mode = wp_headers(site_key)
    print(f"[auth] {site_key} -> {auth_mode}")

    cats = {c["id"]: c["name"] for c in fetch_all(wp_url, headers, "categories", {"hide_empty": "false"})}
    users = {u["id"]: u.get("slug") or u.get("name") for u in fetch_all(wp_url, headers, "users", {"context": "edit"})}
    print(f"[taxonomia] {len(cats)} categorias, {len(users)} usuarios")

    posts = fetch_all(wp_url, headers, "posts",
                      {"context": "edit", "status": "publish,draft,future,pending,private",
                       "orderby": "date", "order": "asc"})
    print(f"[posts] {len(posts)} recuperados")

    rows = []
    for p in posts:
        meta = p.get("meta") or {}
        content = (p.get("content") or {}).get("raw") or ""
        title = (p.get("title") or {}).get("raw") or (p.get("title") or {}).get("rendered", "")
        h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", content, re.I | re.S)
        rows.append({
            "id": p["id"],
            "date_gmt": p.get("date_gmt"),
            "modified_gmt": p.get("modified_gmt"),
            "status": p.get("status"),
            "author_id": p.get("author"),
            "author": users.get(p.get("author"), f"?{p.get('author')}"),
            "slug": p.get("slug"),
            "title": re.sub(r"<[^>]+>", "", title).strip(),
            "link": p.get("link"),
            "categories": [cats.get(c, str(c)) for c in p.get("categories", [])],
            "featured_media": p.get("featured_media"),
            "rank_math_title": meta.get("rank_math_title", ""),
            "rank_math_description": meta.get("rank_math_description", ""),
            "rank_math_focus_keyword": meta.get("rank_math_focus_keyword", ""),
            "rank_math_seo_score": meta.get("rank_math_seo_score", ""),
            "h1_in_body": len(h1s),
            "h1_texts": [re.sub(r"<[^>]+>", "", h).strip() for h in h1s],
            "h2_texts": [re.sub(r"<[^>]+>", "", h).strip()
                         for h in re.findall(r"<h2[^>]*>(.*?)</h2>", content, re.I | re.S)],
            "orphan_li": orphan_li(content),
            "content_chars": len(content),
            "word_count_body": len(re.sub(r"<[^>]+>", " ", content).split()),
        })

    path = os.path.join(OUT_DIR, f"{site_key}-posts.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"collected_at": datetime.utcnow().isoformat() + "Z",
                   "site": site_key, "auth": auth_mode,
                   "categories": cats, "users": users, "posts": rows}, f,
                  ensure_ascii=False, indent=2)
    print(f"[out] {path}")

    print("\n=== RESUMEN ===")
    print(f"total posts        : {len(rows)}")
    print(f"por estado         : {dict(Counter(r['status'] for r in rows))}")
    print(f"por autor          : {dict(Counter(r['author'] for r in rows))}")
    print(f"sin rank_math_title: {sum(1 for r in rows if not r['rank_math_title'])}")
    print(f"sin rank_math_desc : {sum(1 for r in rows if not r['rank_math_description'])}")
    print(f"sin focus keyword  : {sum(1 for r in rows if not r['rank_math_focus_keyword'])}")
    print(f"sin seo_score      : {sum(1 for r in rows if not r['rank_math_seo_score'])}")
    print(f"Uncategorized      : {sum(1 for r in rows if r['categories'] == ['Uncategorized'])}")
    print(f"sin imagen destacada: {sum(1 for r in rows if not r['featured_media'])}")
    print(f"con <h1> en cuerpo : {sum(1 for r in rows if r['h1_in_body'])}")
    print(f"con <li> huerfanos : {sum(1 for r in rows if r['orphan_li'])}")
    numbered = sum(1 for r in rows if re.search(r"-\d+$", r["slug"] or ""))
    print(f"slug con sufijo -N : {numbered}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "propertyledger")
