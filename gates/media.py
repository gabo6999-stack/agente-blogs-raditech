"""Compuerta 2: imagen destacada obligatoria, unica, con alt y miniaturas vivas."""
from gates import GateResult
from tools import image_registry
from tools.html_tools import normalize_text
from tools.http import BROWSER_UA, probe


def g02_featured_image(site_key: str, media_info: dict, focus_keyword: str = "",
                       image_bytes: bytes = None) -> list[GateResult]:
    """media_info: {'media_id', 'alt_text', 'source_url', 'sizes': {'thumbnail': url,
    'medium': url}, 'unsplash_id', 'width', 'height', 'filename'}"""
    out = []
    media_id = (media_info or {}).get("media_id")

    out.append(GateResult(
        "G02a", "Imagen destacada asignada",
        passed=bool(media_id),
        reason="" if media_id else "el post no tiene featured_media",
        details={"media_id": media_id},
    ))
    if not media_id:
        return out

    alt = (media_info.get("alt_text") or "").strip()
    kw = normalize_text(focus_keyword)
    alt_ok = bool(alt) and len(alt) >= 15
    out.append(GateResult(
        "G02b", "Alt descriptivo en la imagen",
        passed=alt_ok,
        reason="" if alt_ok else ("alt vacio" if not alt else f"alt demasiado corto: {alt!r}"),
        details={"alt": alt},
    ))
    kw_ok = bool(kw) and kw in normalize_text(alt)
    out.append(GateResult(
        "G02c", "El alt incluye la keyword objetivo",
        passed=kw_ok,
        reason="" if kw_ok else f"'{focus_keyword}' no aparece en el alt {alt!r}",
        details={"alt": alt, "focus_keyword": focus_keyword},
    ))

    if image_bytes is not None:
        dup = image_registry.check(
            site_key, image_bytes, filename=media_info.get("filename", ""),
            width=media_info.get("width"), height=media_info.get("height"),
            unsplash_id=media_info.get("unsplash_id", ""))
        out.append(GateResult(
            "G02d", "Imagen no repetida en el sitio (SHA-256 + nombre + dimensiones)",
            passed=not dup["duplicate"],
            reason=dup["reason"],
            details={"hash": dup["hash"], "match": dup["match"],
                     "registradas": image_registry.count(site_key)},
        ))

    sizes = media_info.get("sizes") or {}
    faltantes, codigos = [], {}
    for size in ("thumbnail", "medium"):
        url = sizes.get(size)
        if not url:
            faltantes.append(f"{size}: no generado por WordPress")
            continue
        r = probe(url, ua=BROWSER_UA, retries=1)
        codigos[size] = {"url": url, "status": r["status"], "ms": r["ms"]}
        if r["status"] != 200:
            faltantes.append(f"{size}: HTTP {r['status']} en {url}")
    out.append(GateResult(
        "G02e", "Miniaturas thumbnail y medium responden 200",
        passed=not faltantes,
        reason="; ".join(faltantes),
        details=codigos,
    ))
    return out
