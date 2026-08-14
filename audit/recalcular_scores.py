"""Corre "Recalculate Scores" de Rank Math (Status & Tools) y mide qué hizo.

Es una escritura en bloque sobre el meta `rank_math_seo_score` de todos los posts.
No toca contenido. Antes de pulsar se guarda un snapshot completo de las notas
actuales en audit/evidence/, para saber exactamente qué cambió y poder revertirlo.

La pregunta que responde: ¿la nota que calcula esta herramienta coincide con la que
muestra el editor? Si coincidiera, se podría leer por REST y ahorrarse el navegador
de la compuerta 1. Si no, sigue haciendo falta el editor.
"""
import json
import os
import sys
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATA_DIR", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state"))

from playwright.sync_api import sync_playwright  # noqa: E402

from audit.collect_evidence import wp_headers  # noqa: E402
from config import SITES  # noqa: E402

SITE = sys.argv[1] if len(sys.argv) > 1 else "propertyledger"
site = SITES[SITE]
base = site["wp_url"].rstrip("/")
EV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")
wp_url, headers, _ = wp_headers(SITE)


def snapshot():
    """{post_id: (slug, status, score)} de todos los posts."""
    out, page = {}, 1
    while True:
        r = requests.get(f"{wp_url}/wp-json/wp/v2/posts", headers=headers,
                         params={"context": "edit", "per_page": 100, "page": page,
                                 "status": "publish,draft,future,pending,private"}, timeout=45)
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        for p in batch:
            out[p["id"]] = {"slug": p.get("slug"), "status": p.get("status"),
                            "score": (p.get("meta") or {}).get("rank_math_seo_score", "")}
        if len(batch) < 100:
            break
        page += 1
    return out


print("=== SNAPSHOT ANTES ===")
antes = snapshot()
con = sum(1 for v in antes.values() if v["score"])
print(f"  {len(antes)} posts, {con} con nota, {len(antes)-con} sin nota")
path = os.path.join(EV, f"{SITE}-scores-antes.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump({"tomado": datetime.now(timezone.utc).isoformat(), "posts": antes}, f,
              ensure_ascii=False, indent=2)
print(f"  respaldo -> {path}")

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    p = b.new_context(viewport={"width": 1600, "height": 1300}).new_page()
    p.set_default_timeout(90000)

    p.goto(f"{base}/wp-login.php", wait_until="domcontentloaded")
    p.fill("#user_login", site["wp_user"])
    p.fill("#user_pass", site.get("wp_login_password") or site["wp_password"])
    p.click("#wp-submit")
    p.wait_for_load_state("networkidle")
    print(f"\nlogin -> {'OK' if 'wp-admin' in p.url else p.url}")

    p.on("dialog", lambda d: d.accept())

    p.goto(f"{base}/wp-admin/admin.php?page=rank-math-status&view=tools",
           wait_until="domcontentloaded")
    p.wait_for_timeout(7000)

    clicado = p.evaluate("""() => {
        const btns = [...document.querySelectorAll('button, a.button, input[type=button], input[type=submit]')];
        for (const el of btns) {
            const t = (el.innerText || el.value || '').toLowerCase();
            if (!t.includes('recalculate')) continue;
            el.scrollIntoView({block: 'center'});
            el.click();
            const fila = el.closest('tr, .rank-math-box, .cmb-row');
            return (el.innerText || el.value || '').trim() + ' || ' +
                   (fila ? fila.innerText.replace(/\\s+/g, ' ').slice(0, 140) : '');
        }
        return null;
    }""")
    print(f"\n=== boton pulsado ===\n  {clicado or '(NO encontrado)'}")

    if clicado:
        # la herramienta trabaja por lotes via ajax; se espera a que pare
        for i in range(24):
            p.wait_for_timeout(10000)
            estado = p.evaluate("""() => {
                const t = document.body.innerText;
                const m = t.match(/(\\d+)\\s*\\/\\s*(\\d+)/g);
                return {progreso: m ? m.slice(-3).join(' ') : '',
                        hecho: /completed|finished|done|complet/i.test(t)};
            }""")
            print(f"  [{(i+1)*10}s] progreso={estado['progreso'][:40]} hecho={estado['hecho']}")
            if estado["hecho"] and i >= 1:
                break
        p.screenshot(path=os.path.join(os.environ["DATA_DIR"], "rankmath-shots",
                                       f"{SITE}-recalculate.png"), full_page=True)
    b.close()

print("\n=== SNAPSHOT DESPUES ===")
despues = snapshot()
con2 = sum(1 for v in despues.values() if v["score"])
print(f"  {len(despues)} posts, {con2} con nota, {len(despues)-con2} sin nota")

print("\n=== CAMBIOS ===")
nuevos, cambiados = [], []
for pid, d in sorted(despues.items()):
    a = antes.get(pid, {})
    if a.get("score") != d["score"]:
        (nuevos if not a.get("score") else cambiados).append(
            (pid, a.get("score", ""), d["score"], d["slug"]))
print(f"  notas nuevas (antes vacias): {len(nuevos)}")
for pid, viejo, nuevo, slug in nuevos:
    print(f"    #{pid}  (vacia) -> {nuevo}   {slug[:52]}")
print(f"  notas que cambiaron de valor: {len(cambiados)}")
for pid, viejo, nuevo, slug in cambiados:
    print(f"    #{pid}  {viejo} -> {nuevo}   {slug[:52]}")

with open(os.path.join(EV, f"{SITE}-scores-despues.json"), "w", encoding="utf-8") as f:
    json.dump({"tomado": datetime.now(timezone.utc).isoformat(), "posts": despues}, f,
              ensure_ascii=False, indent=2)
