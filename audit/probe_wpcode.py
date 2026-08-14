"""Lista los snippets de WPCode (solo lectura).

WPCode Lite inyecta PHP arbitrario y es el unico plugin activo en propertyledger.us
capaz de filtrar el sitemap de Rank Math. No hay ningun plugin de cache, el sitemap
se genera en vivo y aun asi excluye 28 de 32 posts: si algo lo filtra, esta aqui.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATA_DIR", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state"))

from playwright.sync_api import sync_playwright  # noqa: E402

from config import SITES  # noqa: E402

SITE = sys.argv[1] if len(sys.argv) > 1 else "propertyledger"
site = SITES[SITE]
base = site["wp_url"].rstrip("/")

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    p = b.new_context(viewport={"width": 1700, "height": 1300}).new_page()
    p.set_default_timeout(60000)

    p.goto(f"{base}/wp-login.php", wait_until="domcontentloaded")
    p.fill("#user_login", site["wp_user"])
    p.fill("#user_pass", site.get("wp_login_password") or site["wp_password"])
    p.click("#wp-submit")
    p.wait_for_load_state("networkidle")
    print("login ->", "OK" if "wp-admin" in p.url else p.url)

    p.goto(f"{base}/wp-admin/admin.php?page=wpcode", wait_until="domcontentloaded")
    p.wait_for_timeout(7000)

    print("\n=== snippets de WPCode ===")
    print(p.evaluate("""() => {
        const filas = [...document.querySelectorAll('table tr, .wpcode-list-item')];
        const out = [];
        filas.forEach(f => {
            const t = (f.innerText || '').trim().replace(/\\s+/g, ' ');
            if (t && t.length > 3) out.push(t.slice(0, 150));
        });
        return out.slice(0, 30).join('\\n');
    }"""))

    # enlaces de edicion, para poder abrir cada snippet
    enlaces = p.evaluate("""() => [...document.querySelectorAll('a')]
        .map(a => a.href)
        .filter(h => /page=wpcode-snippet-manager|snippet_id=/.test(h))
        .filter((v, i, s) => s.indexOf(v) === i)
        .slice(0, 12)""")
    print(f"\n=== {len(enlaces)} snippets para inspeccionar ===")

    for url in enlaces:
        p.goto(url, wait_until="domcontentloaded")
        p.wait_for_timeout(5000)
        info = p.evaluate("""() => {
            const t = document.querySelector('#wpcode-snippet-title, input[name="wpcode_snippet_title"]');
            const cm = document.querySelector('.CodeMirror');
            let codigo = '';
            if (cm && cm.CodeMirror) codigo = cm.CodeMirror.getValue();
            if (!codigo) {
                const ta = document.querySelector('textarea[name="wpcode_snippet_code"], #wpcode_snippet_code');
                if (ta) codigo = ta.value;
            }
            const activo = document.querySelector('.wpcode-checkbox-toggle input, #wpcode_active');
            return {titulo: t ? (t.value || t.innerText) : '(sin titulo)',
                    activo: activo ? activo.checked : null,
                    codigo: (codigo || '').slice(0, 1200)};
        }""")
        print("\n" + "=" * 74)
        print(f"SNIPPET: {info['titulo']}   activo={info['activo']}")
        print("=" * 74)
        print(info["codigo"] or "  (no se pudo leer el codigo)")

    b.close()
