"""Compuerta 10: ritmo de publicacion, y parada de emergencia ante rafagas.

Reglas: maximo 2 articulos por dia por sitio, minimo 4 horas entre publicaciones.
Mas de 3 publicaciones en menos de una hora se considera un fallo del agente y
levanta una parada de emergencia que hay que quitar a mano.

Evidencia: el 12-ago-2026 salieron 8 articulos en propertyledger.us, 7 de ellos
entre las 00:11 y la 01:10 UTC — separaciones de 0.05h, 0.07h, 0.13h, 0.62h,
0.07h y 0.06h.

El historico se lee de WordPress, no de un log local: el log vivia en un DATA_DIR
efimero y se perdia en cada redeploy.
"""
from datetime import datetime, timedelta, timezone

from gates import GateResult
from tools import store

MAX_POR_DIA = 2
MIN_HORAS_ENTRE = 4
RAFAGA_N = 3
RAFAGA_VENTANA_H = 1
HALT_KEY = "emergency-halt"


def _parse(dt: str):
    if not dt:
        return None
    try:
        return datetime.fromisoformat(dt.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def is_halted(site_key: str) -> dict | None:
    h = store.load(site_key, HALT_KEY, None)
    return h if h and h.get("active") else None


def halt(site_key: str, reason: str, details=None) -> dict:
    h = {"active": True, "reason": reason, "details": details,
         "since": datetime.now(timezone.utc).isoformat()}
    store.save(site_key, HALT_KEY, h)
    print(f"[PARADA DE EMERGENCIA] {site_key}: {reason}")
    return h


def clear_halt(site_key: str) -> dict:
    h = {"active": False, "cleared_at": datetime.now(timezone.utc).isoformat()}
    store.save(site_key, HALT_KEY, h)
    return h


def g10_publish_rate(site_key: str, published_dates_gmt: list, now: datetime = None) -> list[GateResult]:
    """published_dates_gmt: fechas date_gmt de los posts YA publicados en el sitio."""
    now = now or datetime.now(timezone.utc)
    fechas = sorted([d for d in (_parse(x) for x in published_dates_gmt) if d])
    out = []

    parada = is_halted(site_key)
    out.append(GateResult(
        "G10a", "Sin parada de emergencia activa",
        passed=not parada,
        reason="" if not parada else
               f"parada activa desde {parada.get('since')}: {parada.get('reason')}. "
               f"Se quita a mano con POST /halt/{site_key}/clear",
        details=parada,
    ))

    hoy = [d for d in fechas if d >= now - timedelta(hours=24)]
    out.append(GateResult(
        "G10b", f"Maximo {MAX_POR_DIA} articulos por dia",
        passed=len(hoy) < MAX_POR_DIA,
        reason="" if len(hoy) < MAX_POR_DIA else
               f"ya hay {len(hoy)} publicados en las ultimas 24h: "
               f"{[d.isoformat() for d in hoy]}",
        details={"ultimas_24h": [d.isoformat() for d in hoy]},
    ))

    ultima = fechas[-1] if fechas else None
    horas = (now - ultima).total_seconds() / 3600 if ultima else 999
    out.append(GateResult(
        "G10c", f"Minimo {MIN_HORAS_ENTRE}h desde la publicacion anterior",
        passed=horas >= MIN_HORAS_ENTRE,
        reason="" if horas >= MIN_HORAS_ENTRE else
               f"solo {horas:.2f}h desde el ultimo post ({ultima.isoformat() if ultima else '-'})",
        details={"ultima_publicacion": ultima.isoformat() if ultima else None,
                 "horas_transcurridas": round(horas, 2)},
    ))

    ventana = [d for d in fechas if d >= now - timedelta(hours=RAFAGA_VENTANA_H)]
    hay_rafaga = len(ventana) > RAFAGA_N
    if hay_rafaga and not parada:
        halt(site_key, f"rafaga detectada: {len(ventana)} publicaciones en {RAFAGA_VENTANA_H}h",
             {"fechas": [d.isoformat() for d in ventana]})
    out.append(GateResult(
        "G10d", f"Sin rafaga (>{RAFAGA_N} publicaciones en {RAFAGA_VENTANA_H}h)",
        passed=not hay_rafaga,
        reason="" if not hay_rafaga else
               f"{len(ventana)} publicaciones en la ultima hora — parada de emergencia activada",
        details={"ventana": [d.isoformat() for d in ventana]},
    ))
    return out


def audit_history(published_dates_gmt: list) -> dict:
    """Revisa el historico completo y reporta las violaciones ya ocurridas.
    Sirve para el informe, no para bloquear."""
    fechas = sorted([d for d in (_parse(x) for x in published_dates_gmt) if d])
    por_dia, gaps, rafagas = {}, [], []
    for d in fechas:
        por_dia.setdefault(d.date().isoformat(), []).append(d.isoformat())
    for a, b in zip(fechas, fechas[1:]):
        h = (b - a).total_seconds() / 3600
        if h < MIN_HORAS_ENTRE:
            gaps.append({"de": a.isoformat(), "a": b.isoformat(), "horas": round(h, 2)})
    for i, d in enumerate(fechas):
        ventana = [x for x in fechas[i:] if x <= d + timedelta(hours=RAFAGA_VENTANA_H)]
        if len(ventana) > RAFAGA_N:
            rafagas.append({"inicio": d.isoformat(), "n": len(ventana)})
    return {"dias_sobre_limite": {k: v for k, v in por_dia.items() if len(v) > MAX_POR_DIA},
            "gaps_bajo_minimo": gaps, "rafagas": rafagas}
