"""Opcion B: reimplementacion aproximada del analisis de Rank Math.

QUE ES Y QUE NO ES. Esto es un PRE-FILTRO BARATO, no la puntuacion. Sirve para no
gastar una sesion de navegador en un articulo que obviamente no va a pasar, y para
saber QUE arreglar cuando el numero real sale bajo. El numero que cuenta para la
compuerta 1 es siempre el que devuelve Rank Math en el editor (tools/rankmath_browser.py).

Los pesos son una aproximacion a los tests de Rank Math (Basic SEO + Additional +
Title Readability + Content Readability). No coinciden al decimal con el panel.
"""
import re

from tools.html_tools import analyze, normalize_text, word_count

POWER_WORDS = set("""
free best top guide complete ultimate proven essential simple easy fast quick new
avoid mistakes checklist step steps how why what must need should right wrong
gratis mejor completo esencial simple rapido nuevo evitar errores pasos como
""".split())


def _kw_positions(text: str, kw: str) -> int:
    if not kw:
        return 0
    return len(re.findall(re.escape(kw), text))


def estimate(blog_data: dict, site_url: str = "") -> dict:
    """Devuelve {'score': 0-100, 'tests': [...], 'fallos': [...]}"""
    content = blog_data.get("content", "") or ""
    title = blog_data.get("rank_math_title") or blog_data.get("title", "") or ""
    desc = blog_data.get("rank_math_description", "") or ""
    kw = (blog_data.get("rank_math_focus_keyword", "") or "").strip()
    slug = blog_data.get("slug", "") or ""
    alt = blog_data.get("_image_alt", "") or ""

    a = analyze(content)
    plain = normalize_text(content)
    nkw = normalize_text(kw)
    words = word_count(content)
    tests = []

    def t(id_, desc_, ok, weight, nota=""):
        tests.append({"id": id_, "test": desc_, "ok": bool(ok), "peso": weight, "nota": nota})

    # ── Basic SEO ────────────────────────────────────────────────────────────
    t("keywordInTitle", "La keyword esta en el titulo SEO",
      nkw and nkw in normalize_text(title), 12,
      f"title={title!r}")
    t("titleStartWithKeyword", "El titulo empieza con la keyword",
      nkw and normalize_text(title).startswith(nkw), 5)
    t("keywordInMetaDescription", "La keyword esta en la meta description",
      nkw and nkw in normalize_text(desc), 6)
    t("keywordInPermalink", "La keyword esta en el slug",
      nkw and nkw.replace(" ", "-") in slug.lower(), 6)
    first_10 = " ".join(plain.split()[:max(1, words // 10)])
    t("keywordIn10Percent", "La keyword aparece en el primer 10% del texto",
      nkw and nkw in first_10, 6)
    t("keywordInContent", "La keyword aparece en el cuerpo",
      nkw and nkw in plain, 6)
    t("lengthContent", "Longitud del contenido >= 1000 palabras",
      words >= 1000, 8, f"{words} palabras")

    # ── Additional ───────────────────────────────────────────────────────────
    subs = " ".join(t_ for _, t_ in a["headings"])
    t("keywordInSubheadings", "La keyword aparece en algun H2/H3",
      nkw and nkw in normalize_text(subs), 5)
    t("keywordInImageAlt", "La keyword aparece en el alt de la imagen",
      nkw and nkw in normalize_text(alt), 4, f"alt={alt!r}")

    ocurrencias = _kw_positions(plain, nkw) if nkw else 0
    densidad = (ocurrencias / words * 100) if words else 0
    t("keywordDensity", "Densidad de keyword entre 0.5% y 2.5%",
      0.5 <= densidad <= 2.5, 6, f"{densidad:.2f}% ({ocurrencias} apariciones / {words} palabras)")

    slug_words = len([w for w in slug.split("-") if w])
    t("lengthPermalink", "Slug de 6 palabras o menos", slug_words <= 6, 4, f"{slug_words} palabras")

    host = re.sub(r"^https?://(www\.)?", "", site_url or "").rstrip("/")
    hrefs = re.findall(r'<a\b[^>]*href=["\']([^"\']+)', content, re.I)
    internos = [h for h in hrefs if host and host in h]
    externos = [h for h in hrefs if h.startswith("http") and (not host or host not in h)]
    t("linksHasInternal", "Tiene enlaces internos", len(internos) >= 3, 6, f"{len(internos)} internos")
    t("linksHasExternals", "Tiene enlaces externos", len(externos) >= 2, 5, f"{len(externos)} externos")
    t("linksNotAllExternals", "No todos los enlaces son externos",
      bool(internos) and bool(externos), 3)

    parrafos = re.findall(r"<p[^>]*>(.*?)</p>", content, re.I | re.S)
    largos = [p for p in parrafos if word_count(p) > 120]
    t("contentHasShortParagraphs", "Sin parrafos de mas de 120 palabras",
      not largos, 4, f"{len(largos)} parrafos largos de {len(parrafos)}")
    t("contentHasAssets", "Tiene tablas o listas (recursos visuales)",
      bool(re.search(r"<(ul|ol|table)\b", content, re.I)), 4)

    # ── Title readability ────────────────────────────────────────────────────
    t("titleHasPowerWords", "El titulo tiene alguna power word",
      bool(set(normalize_text(title).split()) & POWER_WORDS), 3)
    t("titleHasNumber", "El titulo incluye un numero",
      bool(re.search(r"\d", title)), 3, "opcional")
    t("titleLength", "Titulo SEO de 15 a 60 caracteres",
      15 <= len(title) <= 60, 4, f"{len(title)} caracteres")
    t("descriptionLength", "Meta description de 150 a 160 caracteres",
      150 <= len(desc) <= 160, 4, f"{len(desc)} caracteres")

    total = sum(x["peso"] for x in tests)
    ganado = sum(x["peso"] for x in tests if x["ok"])
    score = round(ganado / total * 100) if total else 0

    return {"score": score, "tests": tests,
            "fallos": [x for x in tests if not x["ok"]],
            "palabras": words, "densidad": round(densidad, 2)}


def sugerencias(est: dict) -> str:
    """Texto accionable para pedirle a Claude que itere el articulo."""
    lines = []
    for f in sorted(est["fallos"], key=lambda x: -x["peso"]):
        lines.append(f"- ({f['peso']} pts) {f['test']}" + (f" — {f['nota']}" if f["nota"] else ""))
    return "\n".join(lines) or "(sin fallos detectados por el estimador)"
