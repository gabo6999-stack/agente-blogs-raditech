"""Vacia la cache de sitemap de Rank Math y verifica el resultado.

Usa la herramienta dedicada de Rank Math (Status & Tools -> Database Tools ->
"Clear Sitemap Cache") en vez de guardar los ajustes: guardar reescribe toda la
configuracion y no hace falta tocar nada mas que la cache.

Antes y despues cuenta las URLs de post-sitemap.xml con cache-buster.
"""
import os
import re
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATA_DIR", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state"))

from playwright.sync_api import sync_playwright  # noqa: E402

from config import SITES  # noqa: E402
from tools.http import GOOGLEBOT_UA  # noqa: E402

SITE = sys.argv[1] if len(sys.argv) > 1 else "propertyledger"
site = SITES[SITE]
base = site["wp_url"].rstrip("/")


def contar_sitemap(etiqueta):
    r = requests.get(f"{base}/post-sitemap.xml?nc={etiqueta}",
                     headers={"User-Agent": GOOGLEBOT_UA}, timeout=45)
    locs = re.findall(r"<loc>([^<]+)</loc>", r.text)
    print(f"  post-sitemap.xml [{etiqueta}]: HTTP {r.status_code}, {len(locs)} URLs")
    return locs


print("=== ANTES ===")
antes = contar_sitemap("antes")

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    p = b.new_context(viewport={"width": 1600, "height": 1300}).new_page()
    p.set_default_timeout(60000)

    p.goto(f"{base}/wp-login.php", wait_until="domcontentloaded")
    p.fill("#user_login", site["wp_user"])
    p.fill("#user_pass", site.get("wp_login_password") or site["wp_password"])
    p.click("#wp-submit")
    p.wait_for_load_state("networkidle")
    print(f"\nlogin -> {'OK' if 'wp-admin' in p.url else p.url}")

    p.goto(f"{base}/wp-admin/admin.php?page=rank-math-status&view=tools",
           wait_until="domcontentloaded")
    p.wait_for_timeout(7000)

    print("\n=== herramientas disponibles (antes de tocar nada) ===")
    print(p.evaluate("""() => {
        const out = [];
        document.querySelectorAll('button, a.button, input[type=button], input[type=submit]').forEach(el => {
            const t = (el.innerText || el.value || '').trim();
            const fila = el.closest('tr, .rank-math-box, .cmb-row');
            const ctx = fila ? (fila.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 80) : '';
            if (t) out.push(`[${t}]  ${ctx}`);
        });
        return out.slice(0, 25).join('\\n');
    }"""))

    # Esta version de Rank Math no trae un boton de "Clear Sitemap Cache". La cache
    # del sitemap vive en los transients, asi que se pulsa "Remove transients", que
    # es la herramienta que los borra. No toca contenido ni ajustes.
    objetivo = os.getenv("RM_TOOL", "transient")
    clicado = p.evaluate("""(objetivo) => {
        const btns = [...document.querySelectorAll('button, a.button, input[type=button], input[type=submit]')];
        for (const el of btns) {
            const txt = (el.innerText || el.value || '').toLowerCase();
            if (!txt.includes(objetivo)) continue;
            el.scrollIntoView({block: 'center'});
            el.click();
            const fila = el.closest('tr, .rank-math-box, .cmb-row');
            return (el.innerText || el.value || '').trim() + ' || ' +
                   (fila ? fila.innerText.replace(/\\s+/g,' ').slice(0,90) : '');
        }
        return null;
    }""", objetivo)
    print(f"\n=== boton pulsado ===\n  {clicado or '(NINGUNO encontrado)'}")
    p.wait_for_timeout(9000)

    p.screenshot(path=os.path.join(os.environ["DATA_DIR"], "rankmath-shots",
                                   f"{SITE}-sitemap-tools.png"), full_page=True)
    b.close()

print("\n=== DESPUES ===")
despues = contar_sitemap("despues")

print()
print(f"URLs antes: {len(antes)}   URLs despues: {len(despues)}")
nuevas = [u for u in despues if u not in antes]
if nuevas:
    print(f"{len(nuevas)} URLs nuevas en el sitemap. Primeras 12:")
    for u in nuevas[:12]:
        print(f"  {u}")
else:
    print("Sin cambios: la cache no era el problema, o el boton no existe en esta version.")
