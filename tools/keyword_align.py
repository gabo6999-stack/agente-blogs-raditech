"""Alineación de la focus keyword con el texto: la palanca que más puntos mueve.

Diagnóstico del 14-ago-2026 sobre propertyledger.us, leyendo la puntuación REAL del
editor y cruzándola con el texto:

    #318  Rank Math 22/100  keyword 'outsourced accounting property managers'
          -> 0 apariciones literales en 2.349 palabras. Ni en el título, ni en el
             slug, ni en la descripción. "Basic SEO: 5 Errors".
    #322  Rank Math 64/100  keyword 'HOA condo financial statements'
          -> 0 apariciones literales en 2.710 palabras. "Basic SEO: 3 Errors".
    #216  Rank Math 76/100  keyword 'trust accounting QuickBooks property management'
          -> sí aparece en título, slug y descripción. "Basic SEO: All Good".

El patrón es el mismo en los tres: **Rank Math exige la FRASE EXACTA**. El artículo
de #318 dice "outsourced accounting *for* property managers" y la keyword era sin el
"for", así que para Rank Math no aparece ni una sola vez. Como `keywordInTitle`
arrastra a otros seis tests, un desajuste de una preposición hunde la nota entera.

La causa de fondo: el redactor inventaba la keyword y el texto por separado, y una
keyword que suena natural casi nunca aparece literal en prosa natural.

Este módulo convierte la keyword en una restricción del texto, no en una etiqueta
que se pega después.
"""
import re

from tools.html_tools import normalize_text, word_count

DENSIDAD_MIN = 0.5
DENSIDAD_MAX = 2.5


def _cuenta(texto_normalizado: str, kw_normalizada: str) -> int:
    if not kw_normalizada:
        return 0
    return len(re.findall(re.escape(kw_normalizada), texto_normalizado))


def analizar(blog_data: dict) -> dict:
    """Devuelve dónde aparece la keyword literalmente y qué falta."""
    kw = (blog_data.get("rank_math_focus_keyword") or "").strip()
    nkw = normalize_text(kw)
    contenido = blog_data.get("content", "") or ""
    ncontenido = normalize_text(contenido)
    palabras = word_count(contenido)

    titulo_seo = blog_data.get("rank_math_title", "") or ""
    titulo = blog_data.get("title", "") or ""
    desc = blog_data.get("rank_math_description", "") or ""
    slug = blog_data.get("slug", "") or ""
    alt = blog_data.get("_image_alt", "") or ""

    primer_10 = " ".join(ncontenido.split()[:max(30, palabras // 10)])
    h2s = " ".join(re.findall(r"<h2[^>]*>(.*?)</h2>", contenido, re.I | re.S))

    apariciones = _cuenta(ncontenido, nkw)
    densidad = (apariciones / palabras * 100) if palabras else 0.0

    presencia = {
        "titulo_seo": bool(nkw) and nkw in normalize_text(titulo_seo),
        "titulo_h1": bool(nkw) and nkw in normalize_text(titulo),
        "slug": bool(nkw) and nkw.replace(" ", "-") in slug.lower(),
        "descripcion": bool(nkw) and nkw in normalize_text(desc),
        "primer_10_por_ciento": bool(nkw) and nkw in primer_10,
        "cuerpo": apariciones > 0,
        "algun_h2": bool(nkw) and nkw in normalize_text(h2s),
        "alt_imagen": bool(nkw) and nkw in normalize_text(alt),
    }

    objetivo = max(5, round(palabras * 0.008))   # ~0.8%, centro del rango sano
    faltan = max(0, objetivo - apariciones)

    deficits = []
    if not nkw:
        deficits.append("no hay focus keyword")
    else:
        if not presencia["titulo_seo"]:
            deficits.append(
                f"el titulo SEO no contiene la frase exacta '{kw}'. Es el test de mas peso "
                f"y arrastra a otros. Titulo actual: {titulo_seo!r}")
        if not presencia["slug"]:
            deficits.append(f"el slug no contiene '{kw.replace(' ', '-')}'. Slug actual: {slug!r}")
        if not presencia["descripcion"]:
            deficits.append(f"la meta description no contiene la frase exacta '{kw}'")
        if not presencia["primer_10_por_ciento"]:
            deficits.append(f"'{kw}' no aparece en el primer 10% del texto")
        if not presencia["algun_h2"]:
            deficits.append(f"'{kw}' no aparece en ningun <h2>")
        if not presencia["alt_imagen"]:
            deficits.append(f"'{kw}' no aparece en el alt de la imagen destacada")
        if densidad < DENSIDAD_MIN:
            deficits.append(
                f"densidad {densidad:.2f}% (minimo {DENSIDAD_MIN}%): la frase exacta '{kw}' "
                f"aparece {apariciones} veces en {palabras} palabras; hacen falta ~{objetivo} "
                f"(agregar {faltan} mas, repartidas y en frases naturales)")
        elif densidad > DENSIDAD_MAX:
            deficits.append(
                f"densidad {densidad:.2f}% (maximo {DENSIDAD_MAX}%): sobra repeticion, "
                f"quitar algunas apariciones de '{kw}'")

    return {
        "keyword": kw, "presencia": presencia, "apariciones": apariciones,
        "palabras": palabras, "densidad": round(densidad, 2),
        "objetivo_apariciones": objetivo, "deficits": deficits,
        "alineada": not deficits,
    }


def instrucciones(analisis: dict) -> str:
    """Texto accionable para pedirle a Claude que corrija la alineación."""
    if analisis["alineada"]:
        return "(la keyword ya esta alineada)"
    kw = analisis["keyword"]
    lineas = [f'FOCUS KEYWORD OBJETIVO: "{kw}"', "",
              "Rank Math exige la FRASE EXACTA, palabra por palabra. Escribir "
              f'"{kw}" con una preposicion de mas o de menos cuenta como CERO apariciones.',
              "", "Corrige esto:"]
    lineas += [f"- {d}" for d in analisis["deficits"]]
    lineas += ["", "No cambies el tema ni inventes datos: reescribe titulo, descripcion y las "
                   "frases necesarias del cuerpo para que la frase exacta encaje con naturalidad."]
    return "\n".join(lineas)


def derivar_keyword_del_tema(tema: str) -> str:
    """Keyword de partida a partir del tema de la cola, en minusculas y sin
    puntuacion: lo que se le impone al redactor antes de escribir."""
    t = normalize_text(tema)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.split(r"\b(?:a|the|and|or|for|to|in|on|of|with|what|why|how|que|como|por)\b\s*$", t)[0]
    palabras = t.split()
    return " ".join(palabras[:5]).strip()
