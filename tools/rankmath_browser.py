"""Opcion A: leer la puntuacion REAL de Rank Math abriendo el editor de bloques.

Por que hace falta un navegador. La puntuacion SEO de Rank Math se calcula en
JavaScript dentro del editor; no existe como calculo del lado del servidor. El
meta `rank_math_seo_score` solo se escribe cuando alguien abre el post en el editor
y el analisis corre en el navegador. Por eso los 10 posts que propertyledger.us
publico por REST desde el 11-ago-2026 salieron con puntuacion vacia mientras los
anteriores tenian 69-79: a esos alguien los habia abierto en el editor.

Comprobado en la evidencia: los posts #318 y #322 tienen `modified_gmt` 3 y 4
segundos despues de `date_gmt` — nunca los toco un humano — y su
`rank_math_seo_score` esta vacio.

Este modulo hace: login en wp-admin -> abre post.php?post=<id>&action=edit ->
espera a que Rank Math calcule -> lee la puntuacion -> guarda captura del panel.

Requiere Playwright:
    pip install playwright && python -m playwright install chromium
"""
import os
import re

SCREENSHOT_DIR = os.path.join(os.getenv("DATA_DIR", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state")), "rankmath-shots")

# El editor tarda en montar el analisis; estos son los tiempos que usa el flujo.
NAV_TIMEOUT_MS = 60_000
ANALISIS_TIMEOUT_MS = 45_000


class BrowserUnavailable(RuntimeError):
    """Playwright no esta instalado o no hay navegador. NO se traduce en 'pasa':
    sin lectura real, la compuerta 1 falla y el post se queda en borrador."""


def _cerrar_estorbos(page):
    """Cierra lo que tape el panel de Rank Math.

    En los WordPress de Hostinger el asistente 'Kodee' abre un panel flotante que
    se come el lateral derecho y sale en la captura en vez de la puntuacion.
    """
    selectores = [
        "button[aria-label='Close dialog']",
        "button.edit-post-welcome-guide__close",
        ".components-modal__header button[aria-label*='lose']",
    ]
    for sel in selectores:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=800):
                loc.click(timeout=1500)
                page.wait_for_timeout(400)
        except Exception:
            continue
    # El asistente de Hostinger es #chatbot-float-box (360x700, z-index 9996) y se
    # planta encima del lateral derecho, justo donde vive el panel de Rank Math.
    # No tiene un boton de cerrar fiable, asi que se esconde por CSS.
    try:
        page.add_style_tag(content="""
            #chatbot-float-box, .float-box,
            [class*='kodee'], [id*='kodee'],
            .hts-ai-assistant, #hostinger-ai-assistant { display: none !important; }
        """)
    except Exception:
        pass


def _parece_app_password(pw: str) -> bool:
    """Las contraseñas de aplicación de WordPress son 24 caracteres en 6 grupos de 4
    separados por espacios, con el formato 'xxxx xxxx xxxx xxxx xxxx xxxx'."""
    partes = (pw or "").split()
    return len(partes) == 6 and all(len(p) == 4 for p in partes)


def _playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError as e:
        raise BrowserUnavailable(
            "playwright no esta instalado. Instalar con: "
            "pip install playwright && python -m playwright install chromium"
        ) from e


def read_score(site_key: str, post_id: int, headless: bool = True) -> dict:
    """Devuelve {'score': int|None, 'screenshot': path|None, 'metodo': str, 'error': str}"""
    from config import SITES
    site = SITES[site_key]
    base = site["wp_url"].rstrip("/")
    user = site["wp_user"]

    # wp-login.php exige la contraseña REAL de la cuenta. Las contraseñas de
    # aplicación (formato 'xxxx xxxx xxxx xxxx xxxx xxxx') funcionan para la REST
    # API pero son rechazadas por el formulario de acceso, y el editor de bloques
    # sólo carga con sesión de wp-admin.
    password = site.get("wp_login_password") or site["wp_password"]
    if not site.get("wp_login_password") and _parece_app_password(site["wp_password"]):
        raise BrowserUnavailable(
            f"{site_key}: la única credencial configurada es una contraseña de aplicación, "
            f"que wp-login.php no acepta. Definir SITE*_WP_LOGIN_PASSWORD con la contraseña "
            f"real de la cuenta '{user}' para poder leer la puntuación de Rank Math")

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    shot = os.path.join(SCREENSHOT_DIR, f"{site_key}-{post_id}-rankmath.png")
    sync_playwright = _playwright()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        # NO se fija user_agent a mano. Se probo con la cadena de Chrome 120 y el
        # WAF de propertyledger.us respondia 403 hasta en /wp-login.php, con lo que
        # ni siquiera aparecia el campo #user_login. El User-Agent propio del
        # navegador real de Playwright pasa sin problema en los cuatro sitios.
        # (Es el mismo 403 selectivo documentado en tools/http.py, y por eso alli
        # las verificaciones van con el UA de Googlebot.)
        ctx = browser.new_context(viewport={"width": 1600, "height": 1200})
        page = ctx.new_page()
        page.set_default_timeout(NAV_TIMEOUT_MS)
        try:
            # 1. Login en wp-admin. Ojo: la contraseña de aplicacion NO sirve aqui,
            #    wp-login.php exige la contraseña real de la cuenta.
            page.goto(f"{base}/wp-login.php", wait_until="domcontentloaded")
            page.fill("#user_login", user)
            page.fill("#user_pass", password)
            page.click("#wp-submit")
            page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
            if "wp-login.php" in page.url:
                return {"score": None, "screenshot": None, "metodo": "browser",
                        "error": f"login rechazado para {user}: wp-login.php exige la contraseña "
                                 f"real de la cuenta, no la contraseña de aplicacion"}

            # 2. Abrir el post en el editor de bloques
            page.goto(f"{base}/wp-admin/post.php?post={post_id}&action=edit",
                      wait_until="domcontentloaded")
            try:
                page.wait_for_selector(".block-editor, #editor", timeout=NAV_TIMEOUT_MS)
            except Exception:
                pass
            page.wait_for_timeout(6000)   # deja montar los data stores de Gutenberg

            _cerrar_estorbos(page)

            # 3. Esperar a que Rank Math termine el analisis.
            #
            # El selector correcto es getAnalysisScore(), NO getScore() (que no
            # existe en este store). Comprobado el 14-ago-2026 sobre raditech.mx
            # post #1152: `Object.keys(wp.data.select('rank-math'))` expone
            # getAnalysisScore / getKeywords / getSelectedKeyword / getShowScoreFrontend.
            score, metodo = None, ""
            try:
                page.wait_for_function(
                    """() => {
                        try {
                            const s = window.wp && wp.data && wp.data.select('rank-math');
                            if (s && typeof s.getAnalysisScore === 'function') {
                                const v = s.getAnalysisScore();
                                if (typeof v === 'number' && v > 0) return true;
                            }
                        } catch (e) {}
                        const el = document.querySelector('.seo-score .score-text');
                        return !!(el && /\\d/.test(el.textContent));
                    }""",
                    timeout=ANALISIS_TIMEOUT_MS)
            except Exception:
                pass

            try:
                v = page.evaluate("""() => {
                    try {
                        const s = wp.data.select('rank-math');
                        if (s && typeof s.getAnalysisScore === 'function') return s.getAnalysisScore();
                    } catch (e) {}
                    return null;
                }""")
                if isinstance(v, (int, float)) and v > 0:
                    score, metodo = int(v), "wp.data.select('rank-math').getAnalysisScore()"
            except Exception:
                pass

            if score is None:
                # OJO: hay DOS elementos con la clase .rank-math-toolbar-score. El
                # segundo lleva ademas .content-ai-score y muestra la puntuacion de
                # Content AI (0/100 en un post sin Content AI), que no es la de SEO.
                # Hay que excluirlo o se lee un cero que no significa nada.
                try:
                    txt = page.evaluate("""() => {
                        const el = document.querySelector('.seo-score .score-text')
                                || document.querySelector('.seo-score')
                                || document.querySelector('.rank-math-toolbar-score:not(.content-ai-score)');
                        return el ? el.textContent : '';
                    }""")
                    m = re.search(r"(\d{1,3})\s*/\s*100", txt or "")
                    if m:
                        score, metodo = int(m.group(1)), "DOM .seo-score .score-text"
                except Exception:
                    pass

            # 4. Captura del PANEL entero para el reporte.
            #
            # Se prueban los contenedores en orden de preferencia, uno a uno: un
            # selector con comas y .first devuelve el primero en orden del DOM, que
            # resulta ser el `.seo-score` suelto — un recorte de "75 / 100" sin
            # contexto, inservible como evidencia. Lo que hace falta es el panel con
            # la puntuacion Y la lista de comprobaciones.
            try:
                _cerrar_estorbos(page)
                # El lateral arranca en la pestaña "Entrada/Bloque". Hay que pulsar
                # el botón de Rank Math (aria-label="Rank Math", y su propio texto ya
                # es la puntuación) para que el panel se muestre en la captura.
                try:
                    boton = page.locator("button[aria-label='Rank Math']").first
                    if boton.is_visible(timeout=2500):
                        boton.click(timeout=2500)
                        page.wait_for_timeout(2500)
                except Exception:
                    pass
                _cerrar_estorbos(page)
                page.evaluate("""() => {
                    const el = document.querySelector('.seo-score');
                    if (el) el.scrollIntoView({block: 'center'});
                }""")
                page.wait_for_timeout(1200)
                capturado = False
                for sel in (".rank-math-sidebar-panel", ".interface-complementary-area",
                            ".edit-post-sidebar", ".components-panel"):
                    try:
                        loc = page.locator(sel).first
                        if loc.is_visible(timeout=1500):
                            caja = loc.bounding_box()
                            if caja and caja["width"] > 200 and caja["height"] > 200:
                                loc.screenshot(path=shot)
                                capturado = True
                                break
                    except Exception:
                        continue
                if not capturado:
                    page.screenshot(path=shot, full_page=False)
            except Exception:
                try:
                    page.screenshot(path=shot, full_page=False)
                except Exception:
                    shot = None

            if score is None:
                return {"score": None, "screenshot": shot, "metodo": "browser",
                        "error": "el editor cargo pero Rank Math no expuso ninguna puntuacion "
                                 "(revisar la captura)"}
            return {"score": score, "screenshot": shot, "metodo": metodo, "error": None}

        finally:
            try:
                ctx.close()
                browser.close()
            except Exception:
                pass


def read_score_meta(site_key: str, post_id: int) -> str:
    """Lee `rank_math_seo_score` del meta via REST. Solo tiene valor DESPUES de
    que el editor lo haya calculado y guardado; por si solo nunca es prueba."""
    import requests
    from tools.wordpress import get_wp_headers
    wp_url, headers = get_wp_headers(site_key)
    r = requests.get(f"{wp_url}/wp-json/wp/v2/posts/{post_id}",
                     headers=headers, params={"context": "edit"}, timeout=20)
    if r.status_code != 200:
        return ""
    return (r.json().get("meta") or {}).get("rank_math_seo_score", "")
