"""Extrae del editor QUE tests concretos de Rank Math falla cada post, y agrega.

No sirve saber que un post saca 75: hay que saber que 25 puntos perdio y en que.
Esto abre varios posts en el editor, lee la lista de comprobaciones del panel con su
estado (pasa/falla) y cuenta cuales fallan mas veces. De ahi salen los cambios
concretos al prompt del redactor.

    python audit/probe_rankmath_tests.py propertyledger 129 115 119 210
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATA_DIR", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state"))

from playwright.sync_api import sync_playwright  # noqa: E402

from config import SITES  # noqa: E402
from tools.rankmath_browser import _cerrar_estorbos  # noqa: E402

SITE = sys.argv[1] if len(sys.argv) > 1 else "propertyledger"
IDS = [int(x) for x in sys.argv[2:]] or [129, 115]
site = SITES[SITE]
base = site["wp_url"].rstrip("/")

JS_TESTS = """() => {
    const out = [];
    // Rank Math pinta cada comprobacion como un item con clase que incluye
    // 'rank-math-test' y el estado en 'rank-math-passed' / 'rank-math-failed'.
    document.querySelectorAll('[class*="rank-math"]').forEach(el => {
        const cls = (el.className || '').toString();
        if (!/test|result/i.test(cls)) return;
        if (el.querySelector('[class*="rank-math"][class*="test"]')) return;  // solo hojas
        const txt = (el.innerText || '').trim().replace(/\\s+/g, ' ');
        if (!txt || txt.length > 220) return;
        let estado = 'desconocido';
        if (/passed|good|ok\\b/i.test(cls)) estado = 'pasa';
        else if (/failed|bad|error/i.test(cls)) estado = 'falla';
        else if (/warning/i.test(cls)) estado = 'aviso';
        out.push({estado, cls: cls.slice(0, 70), texto: txt.slice(0, 170)});
    });
    return out;
}"""

JS_SECCIONES = """() => {
    const out = [];
    document.querySelectorAll('.components-panel__body, [class*="rank-math"]').forEach(el => {
        const t = (el.innerText || '').trim().replace(/\\s+/g, ' ');
        const m = t.match(/^(Basic SEO|Additional|Title Readability|Content Readability|SEO B.sico|Adicional|Legibilidad[^0-9]*)\\s*(All Good|Todo bien|[0-9]+ Errors?|[0-9]+ Errores?)/i);
        if (m) out.push(m[1].trim() + ' -> ' + m[2]);
    });
    return [...new Set(out)];
}"""

resultados = {}
fallos = Counter()

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1700, "height": 1400})
    p = ctx.new_page()
    p.set_default_timeout(60000)

    p.goto(f"{base}/wp-login.php", wait_until="domcontentloaded")
    p.fill("#user_login", site["wp_user"])
    p.fill("#user_pass", site.get("wp_login_password") or site["wp_password"])
    p.click("#wp-submit")
    p.wait_for_load_state("networkidle")
    print("login ->", "OK" if "wp-admin" in p.url else p.url)

    for pid in IDS:
        p.goto(f"{base}/wp-admin/post.php?post={pid}&action=edit", wait_until="domcontentloaded")
        p.wait_for_timeout(11000)
        _cerrar_estorbos(p)
        try:
            boton = p.locator("button[aria-label='Rank Math']").first
            if boton.is_visible(timeout=4000):
                boton.click()
                p.wait_for_timeout(4000)
        except Exception:
            pass
        # Despliega SOLO los paneles plegados que estan dentro del panel de Rank Math.
        # Un querySelectorAll('[aria-expanded=false]') a nivel de documento pulsa
        # cualquier cosa del editor y provoco una navegacion que destruyo el contexto
        # ("Execution context was destroyed"). En un wp-admin en vivo hay que acotar.
        p.evaluate("""() => {
            const panel = document.querySelector('.rank-math-sidebar-panel')
                       || document.querySelector('.interface-complementary-area');
            if (!panel) return 0;
            const botones = panel.querySelectorAll('.components-panel__body-toggle[aria-expanded="false"]');
            botones.forEach(b => { try { b.click(); } catch (e) {} });
            return botones.length;
        }""")
        p.wait_for_timeout(3500)

        score = p.evaluate("""() => { try { return wp.data.select('rank-math').getAnalysisScore(); } catch(e) { return null; } }""")
        secciones = p.evaluate(JS_SECCIONES)
        tests = p.evaluate(JS_TESTS)
        resultados[pid] = {"score": score, "secciones": secciones, "tests": tests}

        print(f"\n{'='*76}\npost #{pid} — score {score}\n{'='*76}")
        for s in secciones:
            print(f"  {s}")
        malos = [t for t in tests if t["estado"] in ("falla", "aviso")]
        print(f"  --- {len(malos)} comprobaciones no superadas de {len(tests)} ---")
        for t in malos:
            print(f"    [{t['estado']}] {t['texto'][:140]}")
            fallos[t["texto"][:90]] += 1

    b.close()

print()
print("=" * 76)
print("AGREGADO: comprobaciones que fallan en mas posts")
print("=" * 76)
for texto, n in fallos.most_common(25):
    print(f"  x{n}  {texto}")

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence",
                   f"{SITE}-rankmath-tests.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    json.dump(resultados, f, ensure_ascii=False, indent=2)
print(f"\n[out] {out}")
