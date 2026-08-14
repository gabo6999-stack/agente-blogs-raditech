"""Compuertas SEO: G03 (sin duplicados de tema), G04 (slug limpio), G08 (meta de Rank Math)."""
import re

from gates import GateResult
from tools import topic_index
from tools.html_tools import analyze, normalize_text

YEAR = re.compile(r"\b(19|20)\d{2}\b")


def g03_no_duplicate_topic(site_key: str, title: str, content: str,
                           focus_keyword: str = "", slug: str = "",
                           exclude_id: int = None) -> list[GateResult]:
    """Antes de escribir (y otra vez antes de publicar) se compara contra lo ya
    publicado. Si coincide, NO se crea un articulo nuevo: se propone actualizar
    el existente.

    Evidencia: en propertyledger.us habia 9 temas publicados en 2 o 3 URLs, cada
    una auto-canonica. 'Setting Up a Property Management Chart of Accounts the
    Right Way' existia 3 veces (#219, #221, #313).
    """
    h2 = analyze(content or "")["h2_texts"]
    hits = topic_index.find_duplicates(site_key, title, h2, focus_keyword, slug,
                                       exclude_id=exclude_id)
    if hits:
        detalle = "; ".join(f"#{h['id']} ({h['status']}) {h['slug']}: {', '.join(h['motivos'])}"
                            for h in hits[:4])
        return [GateResult(
            "G03", "Sin duplicados de tema", passed=False,
            reason=f"choca con {len(hits)} post(s) existentes -> {detalle}. "
                   f"Propuesta: actualizar #{hits[0]['id']} en vez de crear uno nuevo",
            details={"hits": hits},
        )]
    return [GateResult("G03", "Sin duplicados de tema", passed=True,
                       reason="ningun post existente coincide en titulo, H1, focus keyword ni H2",
                       details={"hits": []})]


def g04_clean_slug(slug: str, title: str = "", wp_returned_slug: str = None) -> list[GateResult]:
    """Slug corto, descriptivo y sin colision.

    El sufijo numerico (`-2`, `-3`) lo agrega WordPress al publicar sobre un slug
    que ya existe. Si aparece, se ABORTA: significa que ese contenido ya esta
    publicado. No es un caso a resolver renombrando. En propertyledger.us quedo
    `security-deposit-accounting-property-managers-compliance-best-practices-2`.
    """
    out = []
    s = (wp_returned_slug or slug or "").strip("/")

    numbered = re.search(r"-(\d+)$", s)
    out.append(GateResult(
        "G04a", "Slug sin sufijo numerico de colision",
        passed=not numbered,
        reason="" if not numbered else
               f"WordPress devolvio '{s}': el sufijo -{numbered.group(1)} significa que "
               f"ese slug YA existe. Se aborta en vez de renombrar",
        details={"slug_propuesto": slug, "slug_devuelto": wp_returned_slug},
    ))

    words = [w for w in s.split("-") if w]
    out.append(GateResult(
        "G04b", "Slug corto (max 6 palabras)",
        passed=len(words) <= 6,
        reason="" if len(words) <= 6 else f"{len(words)} palabras: '{s}'",
        details={"palabras": len(words), "slug": s},
    ))

    has_year = bool(YEAR.search(s))
    out.append(GateResult(
        "G04c", "Slug sin año (salvo contenido anual)",
        passed=not has_year, blocking=False,
        reason="" if not has_year else f"'{s}' lleva año; solo si el contenido es genuinamente anual",
        details={"slug": s},
    ))

    ok_chars = bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", s or ""))
    out.append(GateResult(
        "G04d", "Slug en minusculas, ASCII y con guiones",
        passed=ok_chars,
        reason="" if ok_chars else f"'{s}' tiene caracteres fuera de [a-z0-9-]",
        details={"slug": s},
    ))
    return out


def g08_rankmath_meta(site_key: str, blog_data: dict, exclude_id: int = None) -> list[GateResult]:
    """Los tres campos, siempre, con las longitudes que Rank Math espera y una
    focus keyword que no este ya usada en otro post del sitio."""
    out = []
    title = (blog_data.get("rank_math_title") or "").strip()
    desc = (blog_data.get("rank_math_description") or "").strip()
    fk = (blog_data.get("rank_math_focus_keyword") or "").strip()

    out.append(GateResult(
        "G08a", "rank_math_title presente y <= 60 caracteres",
        passed=bool(title) and len(title) <= 60,
        reason="" if title and len(title) <= 60 else
               ("vacio" if not title else f"{len(title)} caracteres: {title!r}"),
        details={"valor": title, "largo": len(title)},
    ))

    kw_al_principio = bool(fk) and normalize_text(title).startswith(normalize_text(fk)[:max(1, len(fk) // 2)])
    out.append(GateResult(
        "G08b", "Keyword al principio del rank_math_title",
        passed=kw_al_principio, blocking=False,
        reason="" if kw_al_principio else f"'{fk}' no abre el title {title!r}",
        details={"title": title, "focus_keyword": fk},
    ))

    ok_desc = bool(desc) and 150 <= len(desc) <= 160
    out.append(GateResult(
        "G08c", "rank_math_description presente y de 150-160 caracteres",
        passed=ok_desc,
        reason="" if ok_desc else ("vacia" if not desc else f"{len(desc)} caracteres (se piden 150-160)"),
        details={"valor": desc, "largo": len(desc)},
    ))

    kw_en_desc = bool(fk) and normalize_text(fk) in normalize_text(desc)
    out.append(GateResult(
        "G08d", "Keyword dentro de la meta description",
        passed=kw_en_desc,
        reason="" if kw_en_desc else f"'{fk}' no aparece en la description",
        details={"focus_keyword": fk},
    ))

    una_sola = bool(fk) and "," not in fk
    out.append(GateResult(
        "G08e", "Una sola focus keyword",
        passed=una_sola,
        reason="" if una_sola else ("vacia" if not fk else f"trae varias: {fk!r}"),
        details={"focus_keyword": fk},
    ))

    usadas = topic_index.used_focus_keywords(site_key)
    choca = [pid for pid in usadas.get(fk.lower(), []) if pid != exclude_id]
    out.append(GateResult(
        "G08f", "Focus keyword no usada en otro post del sitio",
        passed=not choca,
        reason="" if not choca else f"'{fk}' ya es focus keyword de los posts {choca}",
        details={"focus_keyword": fk, "posts": choca},
    ))

    # G08g/h — la alineacion de la keyword con el texto. Es lo que mas puntos mueve
    # en Rank Math y lo que hundio a los posts del agente: #318 saco 22/100 con la
    # keyword 'outsourced accounting property managers' apareciendo CERO veces en
    # 2.349 palabras, porque el articulo decia "outsourced accounting *for* property
    # managers". Rank Math exige la frase exacta.
    from tools.keyword_align import analizar
    a = analizar(blog_data)
    criticos = ("titulo_seo", "slug", "descripcion", "primer_10_por_ciento", "cuerpo")
    faltan = [k for k in criticos if not a["presencia"][k]]
    out.append(GateResult(
        "G08g", "La focus keyword aparece LITERAL en título, slug, descripción y primer 10%",
        passed=not faltan,
        reason="" if not faltan else
               f"'{fk}' no aparece (frase exacta) en: {', '.join(faltan)}. "
               f"{a['apariciones']} apariciones en {a['palabras']} palabras",
        details=a,
    ))
    out.append(GateResult(
        "G08h", "Densidad de la focus keyword entre 0.5% y 2.5%",
        passed=0.5 <= a["densidad"] <= 2.5,
        reason="" if 0.5 <= a["densidad"] <= 2.5 else
               f"densidad {a['densidad']}% ({a['apariciones']} apariciones en {a['palabras']} "
               f"palabras; se buscan ~{a['objetivo_apariciones']})",
        details={"densidad": a["densidad"], "apariciones": a["apariciones"],
                 "objetivo": a["objetivo_apariciones"]},
    ))
    return out
