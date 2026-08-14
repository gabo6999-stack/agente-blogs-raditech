"""Plan de consolidacion de duplicados con 301.

Agrupa los duplicados reales, elige un ganador por grupo con criterios explicitos,
comprueba el estado HTTP actual de cada URL (sin seguir redirecciones, UA Googlebot)
y cuenta los enlaces internos que apuntan a cada una.

NO ejecuta nada: solo produce el plan. Uso:

    python audit/plan_consolidacion.py propertyledger
"""
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests  # noqa: E402

from audit.collect_evidence import wp_headers  # noqa: E402
from tools.http import GOOGLEBOT_UA, probe  # noqa: E402
from tools.topic_index import normalize_title  # noqa: E402

SITE = sys.argv[1] if len(sys.argv) > 1 else "propertyledger"
EV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")
wp_url, headers, _ = wp_headers(SITE)

with open(os.path.join(EV, f"{SITE}-posts.json"), encoding="utf-8") as f:
    data = json.load(f)
posts = {p["id"]: p for p in data["posts"]}


def cuerpo(pid):
    r = requests.get(f"{wp_url}/wp-json/wp/v2/posts/{pid}", headers=headers,
                     params={"context": "edit"}, timeout=30)
    return r.json()["content"]["raw"] if r.status_code == 200 else ""


# ── 1. Agrupar por titulo normalizado ────────────────────────────────────────
grupos = defaultdict(list)
for p in posts.values():
    grupos[normalize_title(p["title"])].append(p)
dups = {k: v for k, v in grupos.items() if len(v) > 1}

# ── 2. Enlaces internos: quien apunta a quien ───────────────────────────────
print("Leyendo el cuerpo de los 34 posts para contar enlaces internos...")
entrantes = defaultdict(list)
cuerpos = {}
for pid in posts:
    c = cuerpo(pid)
    cuerpos[pid] = c
    for href in re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', c, re.I):
        for otro in posts.values():
            if otro["id"] == pid:
                continue
            if otro["slug"] and f"/{otro['slug']}/" in href:
                entrantes[otro["id"]].append(pid)

# ── 3. Estado HTTP actual ────────────────────────────────────────────────────
print("Comprobando el estado HTTP de cada URL (sin seguir redirecciones, UA Googlebot)...\n")
estado = {}
for p in posts.values():
    if p["status"] != "publish":
        continue
    if not any(p in g for g in dups.values()):
        continue
    estado[p["id"]] = probe(p["link"], ua=GOOGLEBOT_UA, retries=1)


def puntua(p):
    """Criterios de ganador, en orden: responde 200 > antiguedad > mas palabras >
    mas enlaces entrantes > tiene score."""
    st = estado.get(p["id"], {}).get("status")
    return (
        1 if st == 200 else 0,
        -int((p["date_gmt"] or "9999")[:4] + (p["date_gmt"] or "")[5:7] + (p["date_gmt"] or "")[8:10]),
        p["word_count_body"],
        len(entrantes.get(p["id"], [])),
        1 if p["rank_math_seo_score"] else 0,
    )


print("=" * 96)
print(f"PLAN DE CONSOLIDACION — {SITE}")
print("=" * 96)

acciones = []
for i, (clave, grupo) in enumerate(sorted(dups.items()), 1):
    vivos = [p for p in grupo if p["status"] == "publish"]
    if len(vivos) < 2:
        continue
    ganador = max(vivos, key=puntua)
    perdedores = [p for p in vivos if p["id"] != ganador["id"]]

    print(f"\n--- GRUPO {i}: {ganador['title'][:74]}")
    for p in grupo:
        st = estado.get(p["id"], {})
        marca = "GANA  " if p["id"] == ganador["id"] else ("      " if p["status"] != "publish" else "301 ->")
        loc = f"  ya redirige a {st.get('location')}" if st.get("location") else ""
        print(f"  {marca} #{p['id']:<5} {p['status']:<8} HTTP {str(st.get('status') or '-'):<5} "
              f"{p['word_count_body']:>5} pal  score={p['rank_math_seo_score'] or '-':<4} "
              f"entrantes={len(entrantes.get(p['id'], [])):<2} /{p['slug'][:44]}{loc}")

    for p in perdedores:
        st = estado.get(p["id"], {})
        if st.get("status") in (301, 308) and st.get("location"):
            destino_ok = ganador["slug"] in (st.get("location") or "")
            acciones.append({"tipo": "ya_redirige" if destino_ok else "redirige_mal",
                             "de": p, "a": ganador, "actual": st.get("location")})
        else:
            acciones.append({"tipo": "falta_301", "de": p, "a": ganador,
                             "http_actual": st.get("status")})

print()
print("=" * 96)
print("ACCIONES")
print("=" * 96)
falta = [a for a in acciones if a["tipo"] == "falta_301"]
mal = [a for a in acciones if a["tipo"] == "redirige_mal"]
ok = [a for a in acciones if a["tipo"] == "ya_redirige"]

print(f"\n  ya redirigen bien : {len(ok)}")
for a in ok:
    print(f"    #{a['de']['id']} /{a['de']['slug']}/ -> {a['actual']}")

print(f"\n  redirigen al destino equivocado : {len(mal)}")
for a in mal:
    print(f"    #{a['de']['id']} /{a['de']['slug']}/ -> {a['actual']}  (deberia ir a /{a['a']['slug']}/)")

print(f"\n  FALTA crear el 301 : {len(falta)}")
for a in falta:
    print(f"    #{a['de']['id']} (HTTP {a['http_actual']}) /{a['de']['slug']}/")
    print(f"         -> /{a['a']['slug']}/   [#{a['a']['id']}]")
    ent = entrantes.get(a["de"]["id"], [])
    if ent:
        print(f"         enlaces internos que hay que reapuntar: {ent}")

# ── 4. Enlaces internos que apuntan a perdedores ────────────────────────────
print()
print("=" * 96)
print("ENLACES INTERNOS QUE APUNTAN A UN PERDEDOR (hay que reapuntarlos al ganador)")
print("=" * 96)
perdedores_ids = {a["de"]["id"]: a["a"] for a in acciones}
total = 0
for pid_perdedor, ganador in perdedores_ids.items():
    for origen in entrantes.get(pid_perdedor, []):
        total += 1
        print(f"  post #{origen} enlaza a /{posts[pid_perdedor]['slug']}/  "
              f"-> reapuntar a /{ganador['slug']}/")
if not total:
    print("  (ninguno)")

out = os.path.join(EV, f"{SITE}-consolidacion.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump({"acciones": [{"tipo": a["tipo"], "de_id": a["de"]["id"], "de_slug": a["de"]["slug"],
                             "a_id": a["a"]["id"], "a_slug": a["a"]["slug"],
                             "http_actual": a.get("http_actual"), "actual": a.get("actual"),
                             "entrantes": entrantes.get(a["de"]["id"], [])}
                            for a in acciones]}, f, ensure_ascii=False, indent=2)
print(f"\n[out] {out}")
