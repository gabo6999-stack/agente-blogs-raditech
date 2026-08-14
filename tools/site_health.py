"""Chequeo de salud del sitio ANTES de publicar, y verificacion DESPUES.

Origen: el 13-ago-2026 la prueba en tiempo real de Search Console sobre
propertyledger.us devolvio "La pagina no se puede indexar: Error de servidor (5xx)"
y rechazo la solicitud de indexacion. Publicar en un sitio al que Google no llega
no aporta nada y quema presupuesto de rastreo.

Nota honesta sobre la medicion del 14-ago-2026: NO se reprodujo ningun 5xx desde
aqui. Lo que si se midio, estable 3/3 por URL, es que el edge (Cloudflare ->
openresty) devuelve 403 a User-Agents de navegador en varias rutas y 200 a
Googlebot en esas mismas rutas. Por eso el chequeo se hace con el UA de Googlebot:
es el que refleja lo que Google puede rastrear.
"""
import statistics

from tools.html_tools import analyze
from tools.http import GOOGLEBOT_UA, probe

LATENCIA_MAX_MS = 3000


def check(site_key: str, extra_paths: list = None) -> dict:
    """5 peticiones a URLs distintas, sin cache, sin seguir redirecciones."""
    from config import SITES
    base = SITES[site_key]["wp_url"].rstrip("/")
    paths = ["/", "/robots.txt", "/sitemap_index.xml"]
    links = list((SITES[site_key].get("prompt_profile") or {}).get("internal_links", {}).keys())
    for u in links:
        p = u.replace(base, "") or "/"
        if p not in paths:
            paths.append(p)
    paths.extend(extra_paths or [])
    paths = paths[:5] if len(paths) >= 5 else paths

    resultados = [probe(base + p if p.startswith("/") else p, ua=GOOGLEBOT_UA) for p in paths]
    codigos = [r["status"] for r in resultados]
    latencias = [r["ms"] for r in resultados if r["ms"] is not None]
    cincos = [r for r in resultados if r["status"] and 500 <= r["status"] < 600]
    errores = [r for r in resultados if r["status"] is None]
    mediana = statistics.median(latencias) if latencias else None

    ok = not cincos and not errores and (mediana is not None and mediana <= LATENCIA_MAX_MS)
    motivos = []
    if cincos:
        motivos.append(f"{len(cincos)} respuesta(s) 5xx: "
                       f"{[(r['url'], r['status']) for r in cincos]}")
    if errores:
        motivos.append(f"{len(errores)} peticion(es) sin respuesta: "
                       f"{[(r['url'], r['error']) for r in errores]}")
    if mediana is not None and mediana > LATENCIA_MAX_MS:
        motivos.append(f"latencia mediana {mediana:.0f} ms > {LATENCIA_MAX_MS} ms")

    return {"ok": ok, "motivos": motivos, "mediana_ms": mediana,
            "codigos": codigos, "user_agent": "Googlebot",
            "detalle": resultados}


def verify_published(site_key: str, post: dict, content_enviado: str,
                     media_id: int = None) -> dict:
    """Verificacion posterior a la publicacion. Devuelve un dict de checks con la
    respuesta literal de cada peticion."""
    import re

    from config import SITES
    base = SITES[site_key]["wp_url"].rstrip("/")
    url = post.get("link") or ""
    checks = {}

    r = probe(url, ua=GOOGLEBOT_UA)
    checks["1_url_200"] = {
        "ok": r["status"] == 200, "status": r["status"], "location": r["location"],
        "ms": r["ms"], "url": url,
        "nota": "peticion sin seguir redirecciones, UA Googlebot",
        "accion": ("reintentar en 5 min y, si repite, DETENER LA COLA"
                   if r["status"] and r["status"] >= 500 else ""),
    }
    if r["status"] != 200:
        checks["_abortado"] = f"la URL devolvio {r['status']}; no se pudo verificar el HTML"
        return checks

    import requests
    html = requests.get(url, headers={"User-Agent": GOOGLEBOT_UA, "Cache-Control": "no-cache"},
                        allow_redirects=False, timeout=30).text

    esperado = analyze(content_enviado)
    # el H1 de la plantilla se cuenta sobre la pagina completa; los H2 solo del cuerpo
    h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)
    h2s = re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.I | re.S)

    checks["2_contenido_coincide"] = {
        "ok": len(h2s) >= len(esperado["h2_texts"]),
        "h2_enviados": len(esperado["h2_texts"]), "h2_renderizados": len(h2s),
    }
    if media_id:
        media_ok = bool(re.search(r'class="[^"]*wp-post-image', html)) or \
            bool(re.search(rf"wp-image-{media_id}\b", html))
        checks["2b_imagen_destacada_visible"] = {"ok": media_ok, "media_id": media_id}

    orphan = analyze(html)["orphan_li"]
    checks["2c_sin_li_huerfanos"] = {"ok": not orphan, "orphan_li": len(orphan)}

    checks["3_un_solo_h1"] = {
        "ok": len(h1s) == 1, "h1_count": len(h1s),
        "h1_texts": [re.sub(r"<[^>]+>", "", h).strip()[:90] for h in h1s],
    }

    can = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', html, re.I)
    canonical = can.group(1) if can else None
    checks["4_canonical_a_si_mismo"] = {
        "ok": bool(canonical) and canonical.rstrip("/") == url.rstrip("/"),
        "canonical": canonical, "url": url,
    }

    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    desc = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)', html, re.I)
    robots = re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']+)', html, re.I)
    rob_val = (robots.group(1) if robots else "").lower()
    checks["5_metadata_rankmath_en_html"] = {
        "ok": bool(title) and bool(desc) and "noindex" not in rob_val,
        "title": (title.group(1).strip() if title else None),
        "description": (desc.group(1) if desc else None),
        "robots": robots.group(1) if robots else None,
        "index_follow": "noindex" not in rob_val,
    }

    sm = probe(f"{base}/post-sitemap.xml", ua=GOOGLEBOT_UA)
    en_sitemap = None
    if sm["status"] == 200:
        xml = requests.get(f"{base}/post-sitemap.xml",
                           headers={"User-Agent": GOOGLEBOT_UA}, timeout=30).text
        en_sitemap = (post.get("slug") or "") in xml
    checks["6_en_sitemap"] = {
        "ok": bool(en_sitemap), "sitemap_status": sm["status"], "encontrado": en_sitemap,
        "nota": "si en 24h sigue sin aparecer, es problema de configuracion del sitio",
    }

    return checks
