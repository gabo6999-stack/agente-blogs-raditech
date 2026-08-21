"""Analisis y saneamiento del HTML del articulo (compuertas 5 y 7).

Se usa el parser de la libreria estandar en vez de bs4/lxml a proposito: BeautifulSoup
"arregla" el HTML mientras lo lee, asi que sirve para sanear pero NO para validar
(nunca te diria que faltaba un </div>). Aqui hace falta lo contrario: ver el HTML
exactamente como llego.
"""
import re
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}
# Etiquetas que WordPress cierra sola y que el escritor suele dejar abiertas sin
# que eso sea un error real de marcado.
OPTIONAL_CLOSE = {"p", "li", "td", "th", "tr", "thead", "tbody", "option"}


class _Analyzer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack = []
        self.unclosed = []
        self.stray_close = []
        self.orphan_li = []
        self.inline_style = []
        self.headings = []        # [(nivel, texto)]
        self._h = None
        self._htext = []
        self.list_depth = 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag in ("ul", "ol"):
            self.list_depth += 1
        if tag == "li" and self.list_depth == 0:
            self.orphan_li.append(self.getpos())
        if "style" in d:
            self.inline_style.append((tag, d["style"][:60], self.getpos()))
        if re.fullmatch(r"h[1-6]", tag):
            self._h = int(tag[1])
            self._htext = []
        if tag not in VOID:
            self.stack.append((tag, self.getpos()))

    def handle_startendtag(self, tag, attrs):
        d = dict(attrs)
        if "style" in d:
            self.inline_style.append((tag, d["style"][:60], self.getpos()))

    def handle_endtag(self, tag):
        if tag in ("ul", "ol"):
            self.list_depth = max(0, self.list_depth - 1)
        if re.fullmatch(r"h[1-6]", tag) and self._h is not None:
            self.headings.append((self._h, "".join(self._htext).strip()))
            self._h = None
        if tag in VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                # lo que quede por encima queda sin cerrar
                for t, pos in self.stack[i + 1:]:
                    if t not in OPTIONAL_CLOSE:
                        self.unclosed.append((t, pos))
                del self.stack[i:]
                return
        self.stray_close.append((tag, self.getpos()))

    def handle_data(self, data):
        if self._h is not None:
            self._htext.append(data)

    def close(self):
        super().close()
        for t, pos in self.stack:
            if t not in OPTIONAL_CLOSE:
                self.unclosed.append((t, pos))


def analyze(html: str) -> dict:
    p = _Analyzer()
    p.feed(html or "")
    p.close()
    # '&' suelto: un & que no abre una entidad valida
    bare_amp = [m.start() for m in re.finditer(r"&(?!#\d+;|#x[0-9a-fA-F]+;|[a-zA-Z][a-zA-Z0-9]{1,31};)", html or "")]
    return {
        "unclosed": p.unclosed,
        "stray_close": p.stray_close,
        "orphan_li": p.orphan_li,
        "inline_style": p.inline_style,
        "headings": p.headings,
        "bare_amp": bare_amp,
        "h1_count": sum(1 for lvl, _ in p.headings if lvl == 1),
        "h2_texts": [t for lvl, t in p.headings if lvl == 2],
    }


def heading_jumps(headings: list) -> list:
    """Saltos de nivel: un h4 justo despues de un h2, por ejemplo."""
    jumps, prev = [], None
    for lvl, text in headings:
        if prev is not None and lvl > prev + 1:
            jumps.append((prev, lvl, text[:60]))
        prev = lvl
    return jumps


def strip_comment_headers(html: str) -> tuple[str, int]:
    """Quita bloques de comentario tipo brief (`<!-- SEO Title: ... -->`).

    Los 7 posts de la rafaga del 12-ago-2026 empezaban con un comentario que
    llevaba dentro 'SEO Title:', 'Meta Description:', 'Slug:', 'Focus Keyword:'
    e 'Images:'. Es plantilla de briefing pegada al cuerpo, no contenido.
    """
    pattern = re.compile(r"<!--(?:(?!-->).)*?(?:SEO Title|Meta Description|Focus Keyword)"
                         r"(?:(?!-->).)*?-->", re.I | re.S)
    out, n = pattern.subn("", html or "")
    return out.lstrip(), n


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip().lower()


def sanitize(html: str, post_title: str = "") -> tuple[str, list[str]]:
    """Arregla lo mecanico y devuelve (html, lista de cambios aplicados).

    Sanear no sustituye a las compuertas: despues de esto, G05 y G07 vuelven a
    validar. Si algo no se pudo arreglar de forma segura, la compuerta falla.
    """
    changes = []
    out = html or ""

    out, n = strip_comment_headers(out)
    if n:
        changes.append(f"quitados {n} bloque(s) de comentario de briefing (SEO Title/Meta Description)")

    # <h1> en el cuerpo: si repite el titulo del post se elimina (la plantilla ya
    # pone el H1); si dice otra cosa se degrada a <h2> para no perder contenido.
    def _h1(m):
        inner = m.group(1)
        if not post_title or normalize_text(inner) == normalize_text(post_title):
            changes.append("eliminado <h1> del cuerpo (duplicaba el titulo del post)")
            return ""
        changes.append("degradado <h1> del cuerpo a <h2> (texto distinto al titulo)")
        return f"<h2>{inner}</h2>"

    out = re.sub(r"<h1[^>]*>(.*?)</h1>", _h1, out, flags=re.I | re.S)

    # <li> huerfanos: se envuelven los bloques contiguos en un <ul>
    if analyze(out)["orphan_li"]:
        out, k = _wrap_orphan_li(out)
        if k:
            changes.append(f"envueltos {k} bloque(s) de <li> sueltos en <ul>")

    # atributos style en linea
    styled = analyze(out)["inline_style"]
    if styled:
        out = re.sub(r'\s+style\s*=\s*"[^"]*"', "", out)
        out = re.sub(r"\s+style\s*=\s*'[^']*'", "", out)
        changes.append(f"quitados {len(styled)} atributo(s) style en linea")

    # '&' suelto -> &amp; (sin tocar los que ya son entidades ni los de dentro de href)
    def _amp(m):
        return "&amp;"
    before = out
    out = re.sub(r"&(?!#\d+;|#x[0-9a-fA-F]+;|[a-zA-Z][a-zA-Z0-9]{1,31};)", _amp, out)
    if out != before:
        changes.append("escapados '&' sueltos como &amp;")

    # JSON-LD suelto (sin <script> que lo envuelva) en cualquier parte del
    # content: pasa cuando el modelo escribe el bloque a mano en vez de dejar
    # que rebuild_faq_jsonld() lo arme (ese SIEMPRE lo envuelve en <script>).
    # OJO: esto NO cubre el caso cmlc (wp_kses_post le quita el <script> a las
    # cuentas 'author' DESPUES de que este sanitize corre, del lado de
    # WordPress) — ese caso se arregla en la fuente con
    # rebuild_faq_jsonld(..., include_script=False) para sitios con
    # faq_schema_via_meta=True. Aqui solo se corta un bloque que NO esta
    # envuelto en <script>, para no tocar el schema legitimo de los sitios
    # que si lo llevan embebido en el content (raditech, tnrvisual,
    # propertyledger).
    for m in re.finditer(r'\{\s*"@context"', out):
        precede = out[:m.start()]
        if re.search(r'<script[^>]*>\s*$', precede, re.I):
            continue  # esta envuelto en <script>: es el schema real, no tocar
        out = precede.rstrip()
        changes.append("cortado un bloque JSON-LD suelto (sin <script>) del content")
        break

    return out.strip(), changes


def _wrap_orphan_li(html: str) -> tuple[str, int]:
    """Envuelve en <ul> las tiradas contiguas de <li> que no estan dentro de lista.

    Trabaja sobre posiciones del texto, no sobre tokens sueltos: hay que envolver
    el ELEMENTO entero (`<li>...</li>`), no solo su etiqueta de apertura.
    """
    # 1) localiza cada <li> huerfano y donde termina su elemento
    spans = []
    depth = 0
    for m in re.finditer(r"<\s*(/?)\s*(ul|ol|li)\b[^>]*>", html, re.I):
        closing, name = m.group(1) == "/", m.group(2).lower()
        if name in ("ul", "ol"):
            depth = max(0, depth - 1) if closing else depth + 1
            continue
        if name == "li" and not closing and depth == 0:
            fin = _end_of_li(html, m.end())
            spans.append((m.start(), fin))

    if not spans:
        return html, 0

    # 2) une las tiradas separadas solo por espacios
    runs = []
    ini, fin = spans[0]
    for s, e in spans[1:]:
        if not html[fin:s].strip():
            fin = e
        else:
            runs.append((ini, fin))
            ini, fin = s, e
    runs.append((ini, fin))

    # 3) inserta <ul>...</ul> de atras hacia adelante para no mover los indices
    out = html
    for ini, fin in reversed(runs):
        out = out[:ini] + "<ul>" + out[ini:fin] + "</ul>" + out[fin:]
    return out, len(runs)


def _end_of_li(html: str, desde: int) -> int:
    """Fin del elemento <li>: su </li>, o el inicio del siguiente <li>/etiqueta de
    bloque si el autor no lo cerro (WordPress cierra <li> sola, asi que pasa)."""
    cierre = re.search(r"</\s*li\s*>", html[desde:], re.I)
    siguiente = re.search(r"<\s*(li|ul|ol|h[1-6]|p|div|table|section)\b", html[desde:], re.I)
    if cierre and (not siguiente or cierre.start() <= siguiente.start()):
        return desde + cierre.end()
    if siguiente:
        return desde + siguiente.start()
    return len(html)


def word_count(html: str) -> int:
    """Cuenta palabras SOLO del cuerpo del articulo. Nunca se le pasa el HTML
    completo de la pagina: eso cuenta menu y footer y da 9.000-12.000 palabras
    parecidas en todos los articulos."""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html or "", flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z#0-9]+;", " ", text)
    return len([w for w in text.split() if any(c.isalnum() for c in w)])
