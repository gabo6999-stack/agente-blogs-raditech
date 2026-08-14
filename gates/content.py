"""Compuertas de estructura del contenido: G05 (un solo H1) y G07 (HTML valido)."""
import re

from gates import GateResult
from tools.html_tools import analyze, heading_jumps


def g05_single_h1(content: str) -> list[GateResult]:
    """El cuerpo NO debe traer ningun <h1>: el H1 lo pone la plantilla a partir
    del titulo. Ademas la jerarquia arranca en <h2> y no salta niveles.

    Evidencia que motiva la compuerta: los 7 posts publicados en propertyledger.us
    el 12-ago-2026 entre 00:11 y 01:10 UTC traian un <h1> en el cuerpo con el
    MISMO texto del titulo, asi que la pagina renderizaba dos H1 identicos.
    """
    a = analyze(content)
    out = []

    out.append(GateResult(
        "G05a", "Un solo H1 por pagina (cuerpo sin <h1>)",
        passed=a["h1_count"] == 0,
        reason="" if a["h1_count"] == 0 else
               f"el cuerpo trae {a['h1_count']} <h1>; la plantilla ya genera uno con el titulo",
        details={"h1_count": a["h1_count"],
                 "h1_texts": [t for lvl, t in a["headings"] if lvl == 1]},
    ))

    levels = [lvl for lvl, _ in a["headings"] if lvl > 1]
    first_bad = levels and levels[0] != 2
    jumps = heading_jumps([(l, t) for l, t in a["headings"] if l > 1])
    out.append(GateResult(
        "G05b", "Jerarquia de encabezados sin saltos",
        passed=not jumps and not first_bad,
        reason="" if not jumps and not first_bad else
               (f"empieza en h{levels[0]} en vez de h2; " if first_bad else "") +
               (f"saltos: {jumps}" if jumps else ""),
        details={"headings": a["headings"], "jumps": jumps},
    ))

    out.append(GateResult(
        "G05c", "Tiene al menos 3 secciones <h2>",
        passed=len(a["h2_texts"]) >= 3,
        reason="" if len(a["h2_texts"]) >= 3 else f"solo {len(a['h2_texts'])} <h2>",
        details={"h2": a["h2_texts"]},
    ))
    return out


def g07_valid_html(content: str) -> list[GateResult]:
    """HTML valido: <li> siempre dentro de <ul>/<ol>, etiquetas balanceadas, sin
    style en linea, con las entidades bien escapadas."""
    a = analyze(content)
    out = []

    out.append(GateResult(
        "G07a", "Todo <li> dentro de <ul>/<ol>",
        passed=not a["orphan_li"],
        reason="" if not a["orphan_li"] else
               f"{len(a['orphan_li'])} <li> sueltos (linea,col): {a['orphan_li'][:6]}",
        details={"orphan_li": a["orphan_li"]},
    ))

    unbalanced = a["unclosed"] + a["stray_close"]
    out.append(GateResult(
        "G07b", "Etiquetas balanceadas",
        passed=not unbalanced,
        reason="" if not unbalanced else
               f"sin cerrar={a['unclosed'][:5]} cierres_sobrantes={a['stray_close'][:5]}",
        details={"unclosed": a["unclosed"], "stray_close": a["stray_close"]},
    ))

    out.append(GateResult(
        "G07c", "Sin atributos style en linea",
        passed=not a["inline_style"],
        reason="" if not a["inline_style"] else f"{len(a['inline_style'])} elementos con style",
        details={"inline_style": a["inline_style"][:10]},
    ))

    out.append(GateResult(
        "G07d", "Entidades HTML correctas (& escapado)",
        passed=not a["bare_amp"],
        reason="" if not a["bare_amp"] else f"{len(a['bare_amp'])} '&' sueltos sin escapar",
        details={"bare_amp_offsets": a["bare_amp"][:10]},
    ))

    bajo = (content or "").lower()
    prohibidas = [t for t in ("<script", "<style", "<iframe") if t in bajo]
    out.append(GateResult(
        "G07e", "Sin <script>, <style> ni <iframe> en el cuerpo",
        passed=not prohibidas,
        reason="" if not prohibidas else
               f"el content trae {prohibidas}; el schema lo inyecta el sistema y los estilos "
               f"van en el tema, no incrustados en el artículo",
        details={"encontradas": prohibidas},
    ))

    # Un artículo no debería llegar envuelto en <div> de maquetación: los 7 posts
    # de la ráfaga del 12-ago venían dentro de <div class="pls-root pls-blog alignfull">
    # con su propio bloque <style> y un @import de Google Fonts.
    divs = len(re.findall(r"<div\b", content or "", re.I))
    out.append(GateResult(
        "G07f", "Sin <div> de maquetación envolviendo el artículo",
        passed=divs == 0, blocking=False,
        reason="" if divs == 0 else f"{divs} <div> en el cuerpo; el artículo debería ser "
                                    f"HTML semántico (h2/h3/p/ul/table)",
        details={"divs": divs},
    ))
    return out
