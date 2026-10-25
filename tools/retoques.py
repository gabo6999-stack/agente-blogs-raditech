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


def _vivo(url: str) -> bool:
    """Mismo criterio que G09d: responde 200 o redireccion, con UA de Googlebot."""
    from tools.http import GOOGLEBOT_UA, probe
    return probe(url, ua=GOOGLEBOT_UA, retries=1)["status"] in (200, 301, 302, 307, 308)


def _quitar_muertos(blog_data: dict, site_url: str) -> list[str]:
    """Quita el <a> de los externos que no responden (deja el texto) y devuelve los
    que SI responden. Un enlace muerto no suma en G09d y le resta al lector."""
    content = blog_data.get("content", "")
    vivos = []
    for u in externos_distintos(content, site_url):
        if _vivo(u):
            vivos.append(u)
        else:
            content = re.sub(r'<a\s[^>]*href="' + re.escape(u) + r'"[^>]*>(.*?)</a>',
                             r"\1", content, flags=re.I | re.S)
            print(f"  [retoque] enlace externo muerto retirado: {u}")
    blog_data["content"] = content
    return vivos


def completar_externos(site_key: str, blog_data: dict, site_url: str) -> bool:
    """Si hay menos de 2 enlaces externos DISTINTOS y VIVOS, pide a Claude (con
    web_search) otro, de una fuente real, y lo agrega antes de la FAQ."""
    actuales = _quitar_muertos(blog_data, site_url)
    if len(actuales) >= MIN_EXTERNOS:
        return True
    descartados = []
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    for _ in range(5):
        content = blog_data.get("content", "")
        if len(actuales) >= MIN_EXTERNOS:
            return True
        resp = client.messages.create(
            model=MODEL, max_tokens=1500,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
            messages=[{"role": "user", "content":
                f"Tema del articulo: {blog_data.get('title', '')!r}. "
                f"Busca con web_search UNA fuente autorizada y REAL (organismo de salud, "
                f"sociedad medica, universidad, NIH, OMS, IAEA, Secretaria de Salud, etc.) "
                f"distinta de estas: {actuales + descartados}. Prefiere paginas HTML "
                f"estables (no PDF). Responde SOLO con una linea: "
                f"URL|nombre corto de la fuente. Sin nada mas."}])
        linea = _texto(resp).splitlines()[-1] if _texto(resp) else ""
        m = re.match(r"\s*(https?://\S+?)\s*\|\s*(.+)", linea)
        if not m or m.group(1) in actuales or (site_url and site_url.split("//")[-1] in m.group(1)):
            continue
        if not _vivo(m.group(1)):
            descartados.append(m.group(1))
            print(f"  [retoque] candidato descartado (no responde): {m.group(1)}")
            continue
        url, nombre = m.group(1), m.group(2).strip()[:80]
        actuales.append(url)
        enlace = f'<a href="{url}" target="_blank" rel="noopener">{nombre}</a>'
        faq = re.search(r"<h2[^>]*>\s*(Preguntas frecuentes|Frequently Asked)", content, re.I)
        bloque = f"<p>Fuente adicional: {enlace}.</p>\n"
        blog_data["content"] = (content[:faq.start()] + bloque + content[faq.start():]
                                if faq else content + "\n" + bloque)
        print(f"  [retoque] enlace externo agregado: {url}")
    return len(actuales) >= MIN_EXTERNOS


_ANCLA = re.compile(r'(<a\s[^>]*href="[^"]+"[^>]*>)(.*?)(</a>)', re.I | re.S)
_VARIANTES = ("conoce {a}", "más sobre {a}", "visita {a}")


def variar_anclas(content: str) -> str:
    """G09b: dos enlaces con el mismo texto de ancla bloquean el post (cmlc:
    'centro médico las conchas' x3). Las repeticiones, a partir de la segunda, se
    reescriben con un prefijo para que la ancla sea distinta SIN quitar el enlace."""
    vistas: dict[str, int] = {}

    def _cambia(m):
        texto = m.group(2)
        if "<" in texto:                       # ancla con HTML adentro: no se toca
            return m.group(0)
        clave = normalize_text(texto)
        n = vistas.get(clave, 0)
        vistas[clave] = n + 1
        if n == 0 or not clave:
            return m.group(0)
        return m.group(1) + _VARIANTES[(n - 1) % len(_VARIANTES)].format(a=texto) + m.group(3)

    return _ANCLA.sub(_cambia, content or "")
