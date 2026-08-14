"""Prueba las compuertas contra el contenido REAL defectuoso, sin tocar WordPress."""
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audit.collect_evidence import wp_headers  # noqa: E402
from gates.content import g05_single_h1, g07_valid_html  # noqa: E402
from gates.seo import g08_rankmath_meta  # noqa: E402
from tools.html_tools import analyze, sanitize, word_count  # noqa: E402
from tools.seo_estimator import estimate, sugerencias  # noqa: E402

SITE = "propertyledger"
wp_url, headers, _ = wp_headers(SITE)

print("=" * 84)
print("1. SANEADO del post #309 (el de la rafaga: <h1> en el cuerpo + comentario de brief)")
print("=" * 84)
r = requests.get(f"{wp_url}/wp-json/wp/v2/posts/309", headers=headers,
                 params={"context": "edit"}, timeout=25)
raw = r.json()["content"]["raw"]
titulo = r.json()["title"]["raw"]

a0 = analyze(raw)
print(f"  ANTES : h1={a0['h1_count']}  li_huerfanos={len(a0['orphan_li'])}  "
      f"style_inline={len(a0['inline_style'])}  amp_sueltos={len(a0['bare_amp'])}  "
      f"palabras={word_count(raw)}")
print(f"          primeros 120 chars: {raw[:120]!r}")

limpio, cambios = sanitize(raw, titulo)
a1 = analyze(limpio)
print(f"  DESPUES: h1={a1['h1_count']}  li_huerfanos={len(a1['orphan_li'])}  "
      f"style_inline={len(a1['inline_style'])}  amp_sueltos={len(a1['bare_amp'])}  "
      f"palabras={word_count(limpio)}")
print(f"          primeros 120 chars: {limpio[:120]!r}")
print("  cambios aplicados:")
for c in cambios:
    print(f"    - {c}")

print()
print("=" * 84)
print("2. COMPUERTAS 5 y 7 sobre el crudo y sobre el saneado")
print("=" * 84)
for etiqueta, html_ in (("CRUDO", raw), ("SANEADO", limpio)):
    print(f"\n  --- {etiqueta} ---")
    for g in g05_single_h1(html_) + g07_valid_html(html_):
        print(f"    [{g.gate}] {g.status:<6} {g.name}" + (f" — {g.reason[:90]}" if g.reason else ""))

print()
print("=" * 84)
print("3. LI HUERFANOS: caso sintetico (la evidencia real no tenia, hay que probarlo aparte)")
print("=" * 84)
malo = "<p>Intro</p><li>uno</li><li>dos</li><h2>Seccion</h2><ul><li>bien</li></ul>"
am = analyze(malo)
print(f"  entrada : {malo}")
print(f"  detecta : {len(am['orphan_li'])} <li> huerfanos en {am['orphan_li']}")
g = g07_valid_html(malo)[0]
print(f"  G07a    : {g.status} — {g.reason}")
arreglado, ch = sanitize(malo, "")
print(f"  saneado : {arreglado}")
print(f"  ahora   : {len(analyze(arreglado)['orphan_li'])} huerfanos")

print()
print("=" * 84)
print("4. ESTIMADOR (Opcion B) sobre el post #309 vs un post bueno (#216)")
print("=" * 84)
for pid in (309, 216):
    rr = requests.get(f"{wp_url}/wp-json/wp/v2/posts/{pid}", headers=headers,
                      params={"context": "edit"}, timeout=25).json()
    meta = rr.get("meta") or {}
    bd = {"content": rr["content"]["raw"], "title": rr["title"]["raw"],
          "slug": rr["slug"], "rank_math_title": meta.get("rank_math_title", ""),
          "rank_math_description": meta.get("rank_math_description", ""),
          "rank_math_focus_keyword": meta.get("rank_math_focus_keyword", ""),
          "_image_alt": ""}
    est = estimate(bd, "https://propertyledger.us")
    print(f"\n  post #{pid} — estimado {est['score']}/100  "
          f"({est['palabras']} palabras, densidad {est['densidad']}%)")
    print(f"    score real de Rank Math en la BD: {meta.get('rank_math_seo_score') or '(vacio)'}")
    print("    fallos principales:")
    for f in sorted(est["fallos"], key=lambda x: -x["peso"])[:5]:
        print(f"      ({f['peso']}) {f['test']}" + (f" — {f['nota']}" if f["nota"] else ""))

print()
print("=" * 84)
print("5. COMPUERTA 8 sobre metadata sintetica")
print("=" * 84)
casos = [
    ("bien", {"rank_math_title": "Trust Accounting Guide for Property Managers",
              "rank_math_description": "Trust accounting explained for property managers: reconcile accounts, avoid commingling and keep owner funds audit-ready with this practical guide today.",
              "rank_math_focus_keyword": "trust accounting"}),
    ("title largo", {"rank_math_title": "A" * 75,
                     "rank_math_description": "x" * 155,
                     "rank_math_focus_keyword": "algo"}),
    ("desc corta", {"rank_math_title": "Corto",
                    "rank_math_description": "muy corta",
                    "rank_math_focus_keyword": "algo"}),
]
for nombre, bd in casos:
    print(f"\n  --- {nombre} ---")
    for g in g08_rankmath_meta(SITE, bd, exclude_id=-1):
        print(f"    [{g.gate}] {g.status:<6} {g.name}" + (f" — {g.reason[:80]}" if g.reason else ""))
