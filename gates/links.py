"""Compuerta 9: enlaces internos verificados de verdad.

Cada enlace se prueba con una peticion que NO sigue redirecciones. Solo cuenta un
200. Un 301 se reescribe al destino final; un 404 se quita.

Motivo: el 14-ago-2026, la lista `internal_links` de config.py para propertyledger
apuntaba a /hoa-condo-accounting/ (404 estable, 3/3, tanto para Chrome como para
Googlebot) y a /hoa-accounting-basics-guide-board-members-treasurers/ (404 para
Googlebot porque el post #115 sigue en BORRADOR). El post #322 los enlazo igual.
"""
import re
from urllib.parse import urlparse

from gates import GateResult
from tools.html_tools import normalize_text
from tools.http import GOOGLEBOT_UA, probe

MIN_INTERNOS = 3
MIN_EXTERNOS = 2


def extract_links(content: str) -> list[dict]:
    out = []
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                         content or "", re.I | re.S):
        out.append({"url": m.group(1).strip(),
                    "anchor": normalize_text(m.group(2)),
                    "raw": m.group(0)})
    return out


def _is_internal(url: str, site_host: str) -> bool:
    try:
        h = urlparse(url).netloc.lower().replace("www.", "")
        return (not h) or h == site_host
    except Exception:
        return False


def verify_links(content: str, site_url: str, service_pages: list = None) -> dict:
    """Verifica todos los enlaces y devuelve el diagnostico + el content corregido
    (301 -> destino final, 404 -> enlace quitado dejando el texto)."""
    host = urlparse(site_url).netloc.lower().replace("www.", "")
    links = extract_links(content)
    internos = [l for l in links if l["url"].startswith("http") and _is_internal(l["url"], host)]
    externos = [l for l in links if l["url"].startswith("http") and not _is_internal(l["url"], host)]

    cache, arreglos = {}, []
    nuevo = content or ""

    for l in internos:
        u = l["url"]
        if u not in cache:
            cache[u] = probe(u, ua=GOOGLEBOT_UA)
        r = cache[u]
        l["status"] = r["status"]
        l["location"] = r["location"]
        l["ms"] = r["ms"]

        if r["status"] in (301, 302, 307, 308) and r["location"]:
            destino = r["location"]
            if destino.startswith("/"):
                destino = f"{site_url.rstrip('/')}{destino}"
            nuevo = nuevo.replace(f'href="{u}"', f'href="{destino}"').replace(
                f"href='{u}'", f"href='{destino}'")
            arreglos.append(f"301: {u} -> {destino} (reescrito al destino final)")
            l["reescrito_a"] = destino
        elif r["status"] == 404 or r["status"] is None:
            # quita el <a> pero conserva el texto del ancla
            nuevo = re.sub(re.escape(l["raw"]),
                           re.search(r"<a\b[^>]*>(.*?)</a>", l["raw"], re.I | re.S).group(1),
                           nuevo, count=1)
            arreglos.append(f"{r['status']}: {u} — enlace retirado (se conserva el texto)")
            l["retirado"] = True

    for l in externos:
        u = l["url"]
        if u not in cache:
            cache[u] = probe(u, ua=GOOGLEBOT_UA, retries=1)
        r = cache[u]
        l.update({"status": r["status"], "location": r["location"], "ms": r["ms"]})

    return {"internos": internos, "externos": externos,
            "content_corregido": nuevo, "arreglos": arreglos}


def g09_internal_links(content: str, site_url: str, service_pages: list = None) -> tuple:
    """Devuelve (lista de GateResult, content_corregido, diagnostico)."""
    v = verify_links(content, site_url, service_pages)
    internos, externos = v["internos"], v["externos"]
    vivos = [l for l in internos if l.get("status") == 200 or l.get("reescrito_a")]
    out = []

    out.append(GateResult(
        "G09a", f"Minimo {MIN_INTERNOS} enlaces internos que responden 200",
        passed=len(vivos) >= MIN_INTERNOS,
        reason="" if len(vivos) >= MIN_INTERNOS else
               f"solo {len(vivos)} enlaces internos vivos de {len(internos)} encontrados",
        details={"total": len(internos), "vivos": len(vivos),
                 "verificados": [{k: l.get(k) for k in
                                  ("url", "anchor", "status", "location", "ms", "reescrito_a", "retirado")}
                                 for l in internos]},
    ))

    anchors = [l["anchor"] for l in vivos if l.get("anchor")]
    variados = len(set(anchors)) >= max(2, len(anchors) - 1) if anchors else False
    out.append(GateResult(
        "G09b", "Anclas descriptivas y variadas",
        passed=variados,
        reason="" if variados else f"anclas repetidas: {[a for a in set(anchors) if anchors.count(a) > 1]}",
        details={"anchors": anchors},
    ))

    servicio = service_pages or []
    a_servicio = [l for l in vivos
                  if any(s.rstrip("/") in (l.get("reescrito_a") or l["url"]).rstrip("/")
                         for s in servicio)]
    out.append(GateResult(
        "G09c", "Al menos 1 enlace a la pagina de servicio pertinente",
        passed=bool(a_servicio),
        reason="" if a_servicio else
               f"ningun enlace apunta a una pagina de servicio ({len(servicio)} configuradas)",
        details={"paginas_servicio": servicio,
                 "encontrados": [l["url"] for l in a_servicio]},
    ))

    ext_ok = [l for l in externos if l.get("status") in (200, 301, 302, 307, 308)]
    out.append(GateResult(
        "G09d", f"Minimo {MIN_EXTERNOS} enlaces externos a fuentes reales",
        passed=len(ext_ok) >= MIN_EXTERNOS,
        reason="" if len(ext_ok) >= MIN_EXTERNOS else
               f"solo {len(ext_ok)} externos alcanzables de {len(externos)}",
        details={"verificados": [{k: l.get(k) for k in ("url", "anchor", "status", "ms")}
                                 for l in externos]},
    ))

    return out, v["content_corregido"], v
