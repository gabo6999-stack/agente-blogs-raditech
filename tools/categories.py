"""Categoría de servicio determinista por tema (migas de pan de cmlc).

El redactor elige `blog_data["category"]` libremente y a veces inventa una que no
existe. Para los sitios que declaran `category_rules` en config.SITES, la categoría
sale del texto (tema + palabra clave + título) por reglas fijas y ordenadas; sin
coincidencia cae a la categoría default del sitio. Sin red y sin crear categorías:
solo devuelve un nombre; quien lo usa decide si existe en WordPress.
"""
import re
import unicodedata

from config import SITES


def _norm(texto: str) -> str:
    """Minúsculas y sin acentos, para comparar contra las palabras clave."""
    t = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _patron(kw: str) -> "re.Pattern":
    # Inicio de palabra siempre. Las claves cortas (tac, mama) exigen palabra
    # completa (con plural opcional) para no entrar en 'contacto' o 'tactil'.
    base = r"\b" + re.escape(kw)
    if len(kw) <= 4:
        base += r"s?\b"
    return re.compile(base)


def pick_category(site_key: str, topic: str, focus_keyword: str, title: str,
                  blog_category: str = "") -> str:
    """Nombre de la categoría para el post.

    Sitios con `category_rules`: la primera regla (en orden) cuya palabra clave
    aparece en tema + keyword + título; si ninguna, la categoría default del sitio.
    Sitios sin reglas: lo que hacía el flujo anterior, `blog_category` o la del sitio.
    """
    site = SITES.get(site_key, {})
    reglas = site.get("category_rules")
    if not reglas:
        return blog_category or site.get("category", "")
    texto = _norm(" ".join([topic or "", focus_keyword or "", title or ""]))
    for nombre, claves in reglas:
        if any(_patron(_norm(k)).search(texto) for k in claves):
            return nombre
    return site.get("category", "")
