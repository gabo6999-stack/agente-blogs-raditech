"""Compuerta 6: categoria real asignada, nunca 'Uncategorized'.

El bug de fondo, comprobado en vivo el 14-ago-2026 contra propertyledger.us:

    GET /wp/v2/categories?search=HOA & Condo Accounting      -> []
    GET /wp/v2/categories?search=HOA &amp; Condo Accounting  -> [(22, 'HOA &amp; Condo Accounting')]

WordPress guarda el nombre con la entidad HTML ya codificada. `get_or_create_category`
buscaba con el '&' literal, no encontraba nada, intentaba CREAR una categoria que ya
existia, WordPress respondia term_exists (no 201), la funcion devolvia None, el payload
salia sin `categories` y WordPress caia al default: Uncategorized. Es exactamente lo que
le paso al post #322 del 13-ago.
"""
from gates import GateResult

PROHIBIDAS = {"uncategorized", "sin categoria", "sin categoría"}


def g06_category(category_names: list, allowed: list = None) -> list[GateResult]:
    """category_names: nombres REALES que WordPress devolvio para el post."""
    out = []
    nombres = [n for n in (category_names or []) if n]
    limpias = [n for n in nombres if n.strip().lower() not in PROHIBIDAS]

    out.append(GateResult(
        "G06a", "El post tiene al menos una categoria",
        passed=bool(nombres),
        reason="" if nombres else "WordPress no devolvio ninguna categoria",
        details={"categorias": nombres},
    ))

    out.append(GateResult(
        "G06b", "Ninguna categoria es 'Uncategorized'",
        passed=bool(limpias) and len(limpias) == len(nombres),
        reason="" if limpias and len(limpias) == len(nombres) else
               f"categorias asignadas: {nombres}",
        details={"categorias": nombres},
    ))

    if allowed:
        from tools.html_tools import normalize_text
        permitidas = {normalize_text(a.replace("&amp;", "&")) for a in allowed}
        fuera = [n for n in limpias
                 if normalize_text(n.replace("&amp;", "&")) not in permitidas]
        out.append(GateResult(
            "G06c", "La categoria existe en el sitio (no se crean nuevas sin aprobacion)",
            passed=not fuera,
            reason="" if not fuera else
                   f"{fuera} no esta entre las categorias reales del sitio: {sorted(allowed)}",
            details={"asignadas": limpias, "permitidas": sorted(allowed)},
        ))
    return out
