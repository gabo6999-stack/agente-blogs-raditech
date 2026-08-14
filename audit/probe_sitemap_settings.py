"""Lee (SIN modificar) los ajustes de sitemap de Rank Math, para entender por que
faltan 28 de 32 posts en post-sitemap.xml."""
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

JS_CAMPOS = """() => {
    const out = [];
    document.querySelectorAll('input, select, textarea').forEach(el => {
        const n = el.name || el.id || '';
        if (!n) return;
        if (el.type === 'hidden') return;
        if (el.type === 'radio' && !el.checked) return;
        let v = (el.type === 'checkbox' || el.type === 'radio')
            ? (el.checked ? '[x]' : '[ ]') : (el.value || '');
        out.push(n + ' = ' + String(v).slice(0, 100));
    });
    return out.slice(0, 60).join('\\n');
}"""

JS_PANELES = """() => {
    const out = [];
    document.querySelectorAll('.cmb-row, .rank-math-tab').forEach(el => {
        const t = (el.innerText || '').trim().replace(/\\s+/g, ' ');
        if (/exclude|sitemap|links per/i.test(t)) out.push(t.slice(0, 160));
    });
    return out.slice(0, 20).join('\\n---\\n');
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    p = b.new_context(viewport={"width": 1600, "height": 1400}).new_page()
    p.set_default_timeout(60000)

    p.goto(f"{base}/wp-login.php", wait_until="domcontentloaded")
    p.fill("#user_login", site["wp_user"])
    p.fill("#user_pass", site.get("wp_login_password") or site["wp_password"])
    p.click("#wp-submit")
    p.wait_for_load_state("networkidle")
    print("login ->", "OK" if "wp-admin" in p.url else p.url)

    for panel, titulo in [("setting-panel-general", "GENERAL"),
                          ("setting-panel-post", "POSTS")]:
        p.goto(f"{base}/wp-admin/admin.php?page=rank-math-options-sitemap#{panel}",
               wait_until="domcontentloaded")
        p.wait_for_timeout(7000)
        print()
        print("=" * 70)
        print(f"AJUSTES DE SITEMAP — {titulo}")
        print("=" * 70)
        print(p.evaluate(JS_CAMPOS))
        print("--- filas con 'exclude' / 'sitemap' / 'links per' ---")
        print(p.evaluate(JS_PANELES))
        p.screenshot(path=os.path.join(os.environ["DATA_DIR"], "rankmath-shots",
                                       f"pl-sitemap-{panel}.png"), full_page=True)

    b.close()
