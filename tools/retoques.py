"""Retoques acotados antes de las compuertas G08c y G09d.

Dos fallos que el redactor repite sin que el pipeline reintente (cmlc, oct-2026):
  - rank_math_description de 145 o 165 caracteres (se piden 150-160)  -> G08c
  - un solo enlace externo distinto (se piden 2)                      -> G09d
Cada retoque es una llamada pequena y NO toca el resto del articulo.
"""
import re

import anthropic

from config import ANTHROPIC_API_KEY, SITES
from tools.html_tools import normalize_text

MODEL = "claude-sonnet-4-5"
DESC_MIN, DESC_MAX = 150, 160
MIN_EXTERNOS = 2
_ENLACE = re.compile(r'<a\s[^>]*href="(https?://[^"]+)"[^>]*>.*?</a>', re.I | re.S)


def _texto(resp) -> str:
    return "".join(b.text for b in resp.content if hasattr(b, "text")).strip()


def _recortar(desc: str) -> str:
    """Recorta a <=160 en limite de palabra; no inventa texto."""
    if len(desc) <= DESC_MAX:
        return desc
    corte = desc[:DESC_MAX].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return corte + "." if not corte.endswith((".", "!", "?")) and len(corte) < DESC_MAX else corte


def ajustar_descripcion(site_key: str, blog_data: dict, intentos: int = 3) -> bool:
    """Deja rank_math_description en 150-160 con la keyword literal. True si lo logra."""
    desc = (blog_data.get("rank_math_description") or "").strip()
    fk = (blog_data.get("rank_math_focus_keyword") or "").strip()
    ok = lambda d: DESC_MIN <= len(d) <= DESC_MAX and normalize_text(fk) in normalize_text(d)
    if ok(desc):
        return True
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    idioma = "inglés" if SITES[site_key].get("language") == "en" else "español de México"
    for _ in range(intentos):
        pista = "alargala" if len(desc) < DESC_MIN else "acortala"
        resp = client.messages.create(
            model=MODEL, max_tokens=300,
            messages=[{"role": "user", "content":
                f"Meta description actual ({len(desc)} caracteres): {desc!r}\n"
                f"Reescribela en {idioma} con entre {DESC_MIN} y {DESC_MAX} caracteres EXACTOS "
                f"({pista}), conservando el sentido y la frase exacta {fk!r}. "
                f"Titulo del articulo: {blog_data.get('title', '')!r}. "
                "Responde SOLO con la descripcion, sin comillas ni explicacion."}])
        nueva = _texto(resp).strip('"\' ')
        if nueva:
            desc = nueva
        if ok(desc):
            break
    if len(desc) > DESC_MAX and normalize_text(fk) in normalize_text(_recortar(desc)):
        desc = _recortar(desc)
    blog_data["rank_math_description"] = desc
    print(f"  [retoque] meta description: {len(desc)} caracteres")
    return DESC_MIN <= len(desc) <= DESC_MAX


def externos_distintos(content: str, site_url: str) -> list[str]:
    host = re.sub(r"^https?://(www\.)?", "", site_url or "").split("/")[0].lower()
    vistos = []
    for m in _ENLACE.finditer(content or ""):
        u = m.group(1)
        if (host and host in u.lower()) or u in vistos:
            continue
        vistos.append(u)
    return vistos


def completar_externos(site_key: str, blog_data: dict, site_url: str) -> bool:
    """Si hay menos de 2 enlaces externos DISTINTOS, pide a Claude (con web_search)
    uno mas, de otra fuente real, y lo agrega en 'Fuentes consultadas'."""
    content = blog_data.get("content", "")
    actuales = externos_distintos(content, site_url)
    if len(actuales) >= MIN_EXTERNOS:
        return True
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    for _ in range(4):
        content = blog_data.get("content", "")
        actuales = externos_distintos(content, site_url)
        if len(actuales) >= MIN_EXTERNOS:
            return True
        resp = client.messages.create(
            model=MODEL, max_tokens=1500,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
            messages=[{"role": "user", "content":
                f"Tema del articulo: {blog_data.get('title', '')!r}. "
                f"Busca con web_search UNA fuente autorizada y REAL (organismo de salud, "
                f"sociedad medica, universidad, NIH, OMS, IAEA, Secretaria de Salud, etc.) "
                f"distinta de estas: {actuales}. Responde SOLO con una linea: "
                f"URL|nombre corto de la fuente. Sin nada mas."}])
        linea = _texto(resp).splitlines()[-1] if _texto(resp) else ""
        m = re.match(r"\s*(https?://\S+?)\s*\|\s*(.+)", linea)
        if not m or m.group(1) in actuales or (site_url and site_url.split("//")[-1] in m.group(1)):
            continue
        url, nombre = m.group(1), m.group(2).strip()[:80]
        enlace = f'<a href="{url}" target="_blank" rel="noopener">{nombre}</a>'
        faq = re.search(r"<h2[^>]*>\s*(Preguntas frecuentes|Frequently Asked)", content, re.I)
        bloque = f"<p>Fuente adicional: {enlace}.</p>\n"
        blog_data["content"] = (content[:faq.start()] + bloque + content[faq.start():]
                                if faq else content + "\n" + bloque)
        print(f"  [retoque] enlace externo agregado: {url}")
    return len(externos_distintos(blog_data.get("content", ""), site_url)) >= MIN_EXTERNOS
