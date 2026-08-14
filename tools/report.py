"""Reporte por artículo: qué compuertas pasó, la puntuación real de Rank Math, la
captura del panel y las URLs verificadas con su código HTTP.

Se guarda en JSON (para la máquina) y en Markdown (para leerlo). Nada aquí infiere
ni resume una verificación: se vuelca el código HTTP y el motivo literal.
"""
import json
import os
from datetime import datetime, timezone

from tools import store

REPORT_DIR = os.path.join(store.DATA_DIR, "reports")


def build(site_key: str, topic: str, gate_report, *, blog_data: dict = None,
          post: dict = None, publicado: bool = False, score: int = None,
          screenshot: str = None, health: dict = None, postcheck: dict = None,
          links: dict = None, image: dict = None, intentos: int = 1) -> dict:
    return {
        "generado": datetime.now(timezone.utc).isoformat(),
        "sitio": site_key,
        "tema": topic,
        "publicado": publicado,
        "post": {
            "id": (post or {}).get("id"),
            "slug": (post or {}).get("slug"),
            "url": (post or {}).get("link"),
            "estado": (post or {}).get("status"),
            "titulo": ((post or {}).get("title") or {}).get("rendered")
                      or (blog_data or {}).get("title"),
        },
        "rank_math": {
            "score_real": score,
            "umbral": int(os.getenv("RANKMATH_MIN_SCORE", "81")),
            "captura_panel": screenshot,
            "intentos_de_iteracion": intentos,
            "rank_math_title": (blog_data or {}).get("rank_math_title"),
            "rank_math_description": (blog_data or {}).get("rank_math_description"),
            "rank_math_focus_keyword": (blog_data or {}).get("rank_math_focus_keyword"),
        },
        "salud_sitio_previa": health,
        "imagen": image,
        "enlaces_verificados": _links_summary(links),
        "compuertas": gate_report.to_dict() if gate_report else None,
        "verificacion_post_publicacion": postcheck,
    }


def _links_summary(links: dict) -> dict:
    if not links:
        return None
    def fila(l):
        return {"url": l.get("url"), "anchor": l.get("anchor"), "http": l.get("status"),
                "location": l.get("location"), "ms": l.get("ms"),
                "reescrito_a": l.get("reescrito_a"), "retirado": l.get("retirado", False)}
    return {
        "nota": "todas las peticiones sin seguir redirecciones, User-Agent Googlebot",
        "internos": [fila(l) for l in links.get("internos", [])],
        "externos": [fila(l) for l in links.get("externos", [])],
        "correcciones": links.get("arreglos", []),
    }


def save(report: dict) -> tuple[str, str]:
    os.makedirs(REPORT_DIR, exist_ok=True)
    stamp = report["generado"].replace(":", "").replace("-", "")[:15]
    base = os.path.join(REPORT_DIR, f"{report['sitio']}-{stamp}")
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    md = to_markdown(report)
    with open(base + ".md", "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[reporte] {base}.md")
    return base + ".json", base + ".md"


def to_markdown(r: dict) -> str:
    L = []
    estado = "PUBLICADO" if r["publicado"] else "EN BORRADOR (no se publicó)"
    L.append(f"# Reporte — {r['sitio']} — {estado}")
    L.append("")
    L.append(f"- **Tema:** {r['tema']}")
    L.append(f"- **Generado:** {r['generado']}")
    p = r["post"]
    L.append(f"- **Post:** #{p['id']} · `{p['slug']}` · estado `{p['estado']}`")
    if p.get("url"):
        L.append(f"- **URL:** {p['url']}")
    L.append(f"- **Título:** {p.get('titulo')}")
    L.append("")

    rm = r["rank_math"]
    L.append("## Puntuación de Rank Math")
    L.append("")
    if rm["score_real"] is None:
        L.append(f"**NO SE PUDO MEDIR.** Umbral exigido: {rm['umbral']}. "
                 f"Sin lectura del editor no hay puntuación válida.")
    else:
        veredicto = "PASA" if rm["score_real"] >= rm["umbral"] else "NO ALCANZA"
        L.append(f"**{rm['score_real']}/100** (umbral {rm['umbral']}) → {veredicto}")
    L.append(f"- Intentos de iteración: {rm['intentos_de_iteracion']}")
    L.append(f"- Captura del panel: `{rm['captura_panel'] or 'no disponible'}`")
    L.append(f"- `rank_math_title`: {rm['rank_math_title']!r}")
    L.append(f"- `rank_math_description`: {rm['rank_math_description']!r}")
    L.append(f"- `rank_math_focus_keyword`: {rm['rank_math_focus_keyword']!r}")
    L.append("")

    if r.get("salud_sitio_previa"):
        h = r["salud_sitio_previa"]
        L.append("## Salud del sitio (previa a publicar)")
        L.append("")
        L.append(f"{'OK' if h['ok'] else 'FALLA'} — latencia mediana "
                 f"{h.get('mediana_ms')} ms, UA {h.get('user_agent')}")
        for m in h.get("motivos", []):
            L.append(f"- {m}")
        L.append("")
        L.append("| HTTP | ms | URL |")
        L.append("|---|---|---|")
        for d in h.get("detalle", []):
            L.append(f"| {d['status']} | {d['ms']} | {d['url']} |")
        L.append("")

    g = r.get("compuertas") or {}
    L.append("## Compuertas de bloqueo")
    L.append("")
    L.append(f"**{g.get('summary', '—')}**")
    L.append("")
    L.append("| # | Compuerta | Estado | Motivo |")
    L.append("|---|---|---|---|")
    for gate in g.get("gates", []):
        motivo = (gate.get("reason") or "").replace("\n", " ").replace("|", "/")[:200]
        L.append(f"| {gate['gate']} | {gate['name']} | {gate['status']} | {motivo} |")
    L.append("")

    if r.get("enlaces_verificados"):
        e = r["enlaces_verificados"]
        L.append("## Enlaces verificados")
        L.append("")
        L.append(f"_{e['nota']}_")
        L.append("")
        L.append("| Tipo | HTTP | URL | Ancla | Acción |")
        L.append("|---|---|---|---|---|")
        for tipo in ("internos", "externos"):
            for l in e.get(tipo, []):
                accion = ("reescrito → " + l["reescrito_a"]) if l.get("reescrito_a") else (
                    "retirado" if l.get("retirado") else "")
                L.append(f"| {tipo[:-1]} | {l['http']} | {l['url']} | {l['anchor']} | {accion} |")
        L.append("")

    if r.get("imagen"):
        i = r["imagen"]
        L.append("## Imagen destacada")
        L.append("")
        for k, v in i.items():
            L.append(f"- **{k}:** {v}")
        L.append("")

    if r.get("verificacion_post_publicacion"):
        L.append("## Verificación posterior a la publicación")
        L.append("")
        L.append("| Comprobación | OK | Detalle |")
        L.append("|---|---|---|")
        for k, v in r["verificacion_post_publicacion"].items():
            if not isinstance(v, dict):
                L.append(f"| {k} | — | {v} |")
                continue
            det = ", ".join(f"{kk}={vv}" for kk, vv in v.items()
                            if kk != "ok" and vv not in (None, "", []))[:180]
            L.append(f"| {k} | {'sí' if v.get('ok') else 'NO'} | {det} |")
        L.append("")

    return "\n".join(L)
