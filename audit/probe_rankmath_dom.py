"""Averigua COMO expone Rank Math la puntuacion en este WordPress concreto.

No adivina selectores: enumera los stores de wp.data, los selectores del store de
Rank Math, el objeto global rankMath y los nodos del DOM que contengan un numero
con pinta de puntuacion. Solo lectura, no guarda nada.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATA_DIR", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state"))

from playwright.sync_api import sync_playwright  # noqa: E402

from config import SITES  # noqa: E402

SITE = sys.argv[1] if len(sys.argv) > 1 else "raditech"
POST = int(sys.argv[2]) if len(sys.argv) > 2 else 1152
site = SITES[SITE]
base = site["wp_url"].rstrip("/")

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1700, "height": 1300})
    page = ctx.new_page()
    page.set_default_timeout(60000)

    page.goto(f"{base}/wp-login.php", wait_until="domcontentloaded")
    page.fill("#user_login", site["wp_user"])
    page.fill("#user_pass", site.get("wp_login_password") or site["wp_password"])
    page.click("#wp-submit")
    page.wait_for_load_state("networkidle")
    print(f"login -> {page.url}")

    page.goto(f"{base}/wp-admin/post.php?post={POST}&action=edit", wait_until="domcontentloaded")
    page.wait_for_timeout(12000)

    print("\n=== 1. stores de wp.data ===")
    print(page.evaluate("""() => {
        try { return Object.keys(wp.data.getSelectors ? wp.data.getSelectors() : {}).join(', ')
                 || Object.keys(wp.data.select('core/editor') ? {} : {}).join(', '); }
        catch(e) { return 'error: ' + e.message; }
    }"""))
    print(page.evaluate("""() => {
        try {
            const stores = wp.data.getSelectors ? Object.keys(wp.data.getSelectors()) : [];
            return JSON.stringify(stores.filter(s => /rank|seo/i.test(s)));
        } catch(e) { return 'error: ' + e.message; }
    }"""))

    print("\n=== 2. selectores del store 'rank-math' ===")
    print(page.evaluate("""() => {
        try {
            const s = wp.data.select('rank-math');
            if (!s) return 'store rank-math no existe';
            return Object.keys(s).join(', ');
        } catch(e) { return 'error: ' + e.message; }
    }"""))

    print("\n=== 3. valores de los selectores que huelen a score ===")
    print(page.evaluate("""() => {
        const out = {};
        try {
            const s = wp.data.select('rank-math');
            if (!s) return 'sin store';
            for (const k of Object.keys(s)) {
                if (!/score|analysis|keyword|result/i.test(k)) continue;
                try {
                    const v = s[k]();
                    out[k] = (typeof v === 'object' && v !== null)
                        ? ('[' + (Array.isArray(v) ? 'array ' + v.length : 'object ' + Object.keys(v).slice(0,8).join('|')) + ']')
                        : v;
                } catch(e) { out[k] = 'throw: ' + e.message; }
            }
        } catch(e) { return 'error: ' + e.message; }
        return JSON.stringify(out, null, 2);
    }"""))

    print("\n=== 4. objeto global rankMath ===")
    print(page.evaluate("""() => {
        try {
            if (typeof rankMath === 'undefined') return 'rankMath no definido';
            const k = Object.keys(rankMath);
            const interesa = {};
            for (const key of k) if (/score|assessor|analy/i.test(key)) {
                try { interesa[key] = typeof rankMath[key]; } catch(e) {}
            }
            return 'claves: ' + k.slice(0,40).join(', ') + '\\ninteresantes: ' + JSON.stringify(interesa);
        } catch(e) { return 'error: ' + e.message; }
    }"""))

    print("\n=== 5. nodos del DOM con pinta de puntuacion ===")
    print(page.evaluate("""() => {
        const hits = [];
        document.querySelectorAll('*').forEach(el => {
            if (el.children.length) return;
            const t = (el.textContent || '').trim();
            if (!t || t.length > 24) return;
            if (!/^\\d{1,3}\\s*(\\/\\s*100)?$/.test(t)) return;
            const cls = el.className && el.className.toString ? el.className.toString() : '';
            const par = el.parentElement ? (el.parentElement.className || '').toString() : '';
            if (!/rank|score|seo/i.test(cls + ' ' + par + ' ' + (el.id||''))) return;
            hits.push({tag: el.tagName, id: el.id, cls: cls.slice(0,70), padre: par.slice(0,70), texto: t});
        });
        return JSON.stringify(hits, null, 2);
    }"""))

    print("\n=== 6. cualquier elemento cuyo class/id mencione score ===")
    print(page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('[class*="score"], [id*="score"], [class*="rank-math"]').forEach(el => {
            const cls = (el.className || '').toString();
            if (!/score/i.test(cls + (el.id||''))) return;
            out.push({tag: el.tagName, id: el.id, cls: cls.slice(0,80),
                      texto: (el.textContent||'').trim().slice(0,60)});
        });
        return JSON.stringify(out.slice(0, 25), null, 2);
    }"""))

    page.screenshot(path=os.path.join(os.environ["DATA_DIR"], "rankmath-shots",
                                      f"probe-{SITE}-{POST}.png"), full_page=False)
    ctx.close()
    b.close()
