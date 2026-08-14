"""Compuerta 1: puntuacion de Rank Math >= 81, leida del editor real.

Nunca se redondea hacia arriba ni se estima. El estimador (tools/seo_estimator.py)
solo decide si vale la pena gastar una sesion de navegador; el numero que cuenta es
el que devuelve Rank Math.

Si el navegador no esta disponible, la compuerta FALLA (no "pasa por defecto"):
sin lectura real no hay forma de saber la puntuacion, y la regla de la casa es que
es preferible no publicar a publicar mal.
"""
import os

from gates import GateResult
from tools import seo_estimator
from tools.rankmath_browser import BrowserUnavailable, read_score

UMBRAL = int(os.getenv("RANKMATH_MIN_SCORE", "81"))
UMBRAL_PREFILTRO = int(os.getenv("RANKMATH_PREFILTER_MIN", "70"))
MAX_INTENTOS = 3


def g01_prefilter(blog_data: dict, site_url: str) -> tuple[GateResult, dict]:
    """Opcion B — pre-filtro barato. No bloquea la publicacion por si mismo: evita
    abrir el navegador para un articulo que claramente no llega."""
    est = seo_estimator.estimate(blog_data, site_url)
    ok = est["score"] >= UMBRAL_PREFILTRO
    return GateResult(
        "G01-pre", f"Pre-filtro (estimador propio) >= {UMBRAL_PREFILTRO}",
        passed=ok, blocking=False,
        reason=f"estimado {est['score']}/100" + ("" if ok else
               f" — por debajo de {UMBRAL_PREFILTRO}, no se gasta sesion de navegador.\n"
               f"Fallos:\n{seo_estimator.sugerencias(est)}"),
        details={"score_estimado": est["score"], "palabras": est["palabras"],
                 "densidad_keyword": est["densidad"],
                 "fallos": [{"test": f["test"], "peso": f["peso"], "nota": f["nota"]}
                            for f in est["fallos"]]},
    ), est


def g01_real_score(site_key: str, post_id: int, headless: bool = True) -> GateResult:
    """Opcion A — la unica que da el numero real."""
    try:
        r = read_score(site_key, post_id, headless=headless)
    except BrowserUnavailable as e:
        return GateResult(
            "G01", f"Puntuacion real de Rank Math >= {UMBRAL}", passed=False,
            reason=f"NO SE PUDO COMPROBAR: {e}. El post se queda en borrador — "
                   f"sin lectura del editor no hay puntuacion que valga",
            details={"score": None, "screenshot": None},
        )
    except Exception as e:
        return GateResult(
            "G01", f"Puntuacion real de Rank Math >= {UMBRAL}", passed=False,
            reason=f"NO SE PUDO COMPROBAR: error del navegador: {e}",
            details={"score": None, "screenshot": None},
        )

    score = r.get("score")
    if score is None:
        return GateResult(
            "G01", f"Puntuacion real de Rank Math >= {UMBRAL}", passed=False,
            reason=f"NO SE PUDO COMPROBAR: {r.get('error')}",
            details=r,
        )
    return GateResult(
        "G01", f"Puntuacion real de Rank Math >= {UMBRAL}",
        passed=score >= UMBRAL,
        reason=f"Rank Math devolvio {score}/100" + ("" if score >= UMBRAL else
               f" — por debajo de {UMBRAL}"),
        details={"score": score, "umbral": UMBRAL, "metodo": r.get("metodo"),
                 "screenshot": r.get("screenshot")},
    )


def necesita_iterar(score: int | None) -> bool:
    """Entre 70 y 80 vale la pena iterar el contenido y volver a medir (max 3
    intentos). Por debajo de 70 el problema es de fondo, no de retoque."""
    return score is not None and 70 <= score < UMBRAL
