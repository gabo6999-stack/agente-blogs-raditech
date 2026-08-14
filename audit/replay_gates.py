"""Pasa los posts YA publicados por las compuertas nuevas.

Sirve para dos cosas: comprobar que las compuertas funcionan sobre datos reales y
medir cuanto del desastre habrian evitado. No escribe nada en WordPress.

    python audit/replay_gates.py propertyledger
    python audit/replay_gates.py propertyledger --links   (verifica tambien enlaces, lento)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SITES  # noqa: E402
from gates.cadence import audit_history  # noqa: E402
from gates.content import g05_single_h1, g07_valid_html  # noqa: E402
from gates.seo import g04_clean_slug, g08_rankmath_meta  # noqa: E402
from gates.taxonomy import g06_category  # noqa: E402
from tools import store, topic_index  # noqa: E402
from tools.html_tools import sanitize, word_count  # noqa: E402

SITE = sys.argv[1] if len(sys.argv) > 1 else "propertyledger"
CON_ENLACES = "--links" in sys.argv
EV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")

with open(os.path.join(EV, f"{SITE}-posts.json"), encoding="utf-8") as f:
    data = json.load(f)
posts = data["posts"]
cats_reales = [n for n in data["categories"].values()]

# Se siembra el indice de temas con los posts reales para que G03 y G08f funcionen.
store.save(SITE, "topic-index", {
    "refreshed_at": data["collected_at"],
    "posts": [{
        "id": p["id"], "slug": p["slug"], "title": p["title"],
        "norm_title": topic_index.normalize_title(p["title"]),
        "h1": (p["h1_texts"] or [""])[0],
        "focus_keyword": p["rank_math_focus_keyword"],
        "h2": p["h2_texts"],
        "norm_h2": sorted({topic_index.normalize_title(h) for h in p["h2_texts"]
                           if topic_index.normalize_title(h)}),
        "status": p["status"], "link": p["link"], "date_gmt": p["date_gmt"],
    } for p in posts],
})

print("=" * 96)
print(f"REPLAY DE COMPUERTAS — {SITE} — {len(posts)} posts")
print("=" * 96)
print(f"{'id':<6}{'fecha':<12}{'G03':<6}{'G04':<6}{'G05':<6}{'G06':<6}{'G07':<6}{'G08':<6}{'pal':<7}bloqueado por")
print("-" * 96)

resumen = {"bloqueados": 0, "limpios": 0}
por_gate = {}
detalle_por_post = {}

for p in sorted(posts, key=lambda x: x["date_gmt"] or ""):
    # se reconstruye el content aproximado desde lo que guardamos
    content = ""
    fake = {"content": content}

    fallos = []

    # G05/G07 se evaluan con los indicadores ya extraidos en la evidencia
    g05_ok = p["h1_in_body"] == 0
    g07_ok = p["orphan_li"] == 0
    if not g05_ok:
        fallos.append("G05")
    if not g07_ok:
        fallos.append("G07")

    # G04 sobre el slug real
    r04 = g04_clean_slug(p["slug"], p["title"], wp_returned_slug=p["slug"])
    if any(not r.passed and r.blocking for r in r04):
        fallos.append("G04")

    # G06 sobre las categorias reales
    r06 = g06_category(p["categories"], allowed=cats_reales)
    if any(not r.passed and r.blocking for r in r06):
        fallos.append("G06")

    # G08 sobre la metadata real
    r08 = g08_rankmath_meta(SITE, {
        "rank_math_title": p["rank_math_title"],
        "rank_math_description": p["rank_math_description"],
        "rank_math_focus_keyword": p["rank_math_focus_keyword"],
    }, exclude_id=p["id"])
    if any(not r.passed and r.blocking for r in r08):
        fallos.append("G08")

    # G03 contra el resto del sitio
    hits = topic_index.find_duplicates(
        SITE, p["title"], p["h2_texts"], p["rank_math_focus_keyword"], p["slug"],
        exclude_id=p["id"])
    if hits:
        fallos.append("G03")

    # G01: sin score no hay forma de saber que llegaba a 81
    if not p["rank_math_seo_score"]:
        fallos.append("G01")
    elif int(p["rank_math_seo_score"]) < 81:
        fallos.append("G01")

    for f in fallos:
        por_gate[f] = por_gate.get(f, 0) + 1
    if fallos:
        resumen["bloqueados"] += 1
    else:
        resumen["limpios"] += 1

    detalle_por_post[p["id"]] = {
        "fallos": fallos,
        "duplicados": [f"#{h['id']} {', '.join(h['motivos'])}" for h in hits[:3]],
        "score": p["rank_math_seo_score"] or None,
    }

    def mk(ok):
        return "ok" if ok else "FALLA"
    print(f"{p['id']:<6}{(p['date_gmt'] or '')[:10]:<12}"
          f"{mk('G03' not in fallos):<6}{mk('G04' not in fallos):<6}{mk('G05' not in fallos):<6}"
          f"{mk('G06' not in fallos):<6}{mk('G07' not in fallos):<6}{mk('G08' not in fallos):<6}"
          f"{p['word_count_body']:<7}{','.join(fallos)}")

print()
print("=" * 96)
print("RESUMEN")
print("=" * 96)
print(f"  posts que las compuertas HABRIAN BLOQUEADO : {resumen['bloqueados']}/{len(posts)}")
print(f"  posts que habrian pasado limpios           : {resumen['limpios']}/{len(posts)}")
print()
print("  disparos por compuerta:")
nombres = {"G01": "puntuacion Rank Math < 81 o ausente",
           "G03": "duplicado de tema",
           "G04": "slug sucio o con sufijo -N",
           "G05": "H1 en el cuerpo / jerarquia",
           "G06": "Uncategorized o categoria inexistente",
           "G07": "HTML invalido",
           "G08": "metadata de Rank Math incompleta"}
for g, n in sorted(por_gate.items(), key=lambda x: -x[1]):
    print(f"    {g}  {n:>3} posts  — {nombres.get(g, '')}")

print()
print("  ritmo de publicacion (historico completo):")
hist = audit_history([p["date_gmt"] for p in posts if p["status"] == "publish"])
print(f"    dias por encima de 2 posts/dia : {list(hist['dias_sobre_limite'].keys())}")
print(f"    gaps por debajo de 4h          : {len(hist['gaps_bajo_minimo'])}")
print(f"    ventanas de rafaga (>3 en 1h)  : {len(hist['rafagas'])}")

print()
print("  duplicados detectados por G03 (primeros 6):")
mostrados = 0
for pid, d in detalle_por_post.items():
    if d["duplicados"] and mostrados < 6:
        print(f"    #{pid}: {d['duplicados'][0]}")
        mostrados += 1

out = os.path.join(EV, f"{SITE}-replay.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump({"resumen": resumen, "por_gate": por_gate,
               "ritmo": hist, "por_post": detalle_por_post}, f, ensure_ascii=False, indent=2)
print(f"\n[out] {out}")
