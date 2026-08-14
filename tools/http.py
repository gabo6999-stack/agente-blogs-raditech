"""Cliente HTTP para verificar URLs.

Dos decisiones que vienen de la auditoria del 13-14 de agosto de 2026 sobre
propertyledger.us y que NO son cosmeticas:

1) NUNCA seguir redirecciones. Un 200 obtenido con allow_redirects=True no
   distingue una pagina viva de un 301 hacia otra cosa. Todas las funciones de
   aqui usan allow_redirects=False.

2) Verificar con el User-Agent de Googlebot. Medicion literal del 14-ago-2026
   sobre propertyledger.us (3 intentos por URL, resultado estable 3/3):

       path                                        Chrome      Googlebot
       /contact/                                   403,403,403 200,200,200
       /property-management-trust-accounting/      403,403,403 200,200,200
       /property-management-financial-statements/  403,403,403 200,200,200
       /property-management-bookkeeping-vs-acc../  403,403,403 301,301,301

   El edge (Cloudflare -> openresty) responde 403 a User-Agents de navegador en
   varias rutas y 200 a Googlebot. Si el verificador de enlaces usara un UA de
   navegador, marcaria como rotos enlaces que Google ve perfectamente. Lo que
   importa para SEO es lo que ve Googlebot, asi que ese es el UA por defecto.
"""
import time

import requests

GOOGLEBOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def probe(url: str, ua: str = GOOGLEBOT_UA, timeout: int = 25, retries: int = 2) -> dict:
    """GET sin seguir redirecciones. Devuelve status, location y latencia.

    Reintenta solo ante error de red o 5xx (pueden ser transitorios); un 403 o un
    404 se devuelven tal cual porque son respuestas legitimas del servidor.
    """
    last = {"url": url, "status": None, "location": None, "ms": None, "error": None}
    for intento in range(retries + 1):
        t0 = time.time()
        try:
            r = requests.get(url, headers={"User-Agent": ua, "Cache-Control": "no-cache",
                                           "Pragma": "no-cache"},
                             allow_redirects=False, timeout=timeout)
            last = {"url": url, "status": r.status_code,
                    "location": r.headers.get("location"),
                    "ms": round((time.time() - t0) * 1000),
                    "error": None, "bytes": len(r.content)}
            if r.status_code < 500:
                return last
        except Exception as e:
            last = {"url": url, "status": None, "location": None,
                    "ms": round((time.time() - t0) * 1000), "error": str(e)[:200]}
        if intento < retries:
            time.sleep(2)
    return last


def resolve_chain(url: str, ua: str = GOOGLEBOT_UA, max_hops: int = 5) -> dict:
    """Sigue la cadena de redirecciones a mano (un salto a la vez, sin
    allow_redirects) para poder reportar cada hop con su codigo."""
    hops, current = [], url
    for _ in range(max_hops):
        r = probe(current, ua=ua)
        hops.append(r)
        if r["status"] in (301, 302, 307, 308) and r["location"]:
            nxt = r["location"]
            if nxt.startswith("/"):
                base = "/".join(current.split("/")[:3])
                nxt = base + nxt
            current = nxt
            continue
        break
    return {"start": url, "final": current, "hops": hops,
            "final_status": hops[-1]["status"] if hops else None}
