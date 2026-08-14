"""Almacenamiento persistente del agente.

Todo lo que el agente necesita RECORDAR entre corridas vive aqui: el indice de
temas publicados, el registro de imagenes y el historial de ritmo de publicacion.

Por que existe este modulo: `tools/logger.py` escribia en `DATA_DIR` con default
"." y `logs/` esta en .gitignore. En Railway sin volumen montado eso significa
que el historial se BORRA en cada redeploy — el agente olvidaba lo que ya habia
publicado y volvia a escribir los mismos temas (de ahi los slugs con sufijo -2).
`DATA_DIR` debe apuntar a un volumen persistente (/data en Railway).
"""
import json
import os
import tempfile
import threading

DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "state"))
STATE_DIR = os.path.join(DATA_DIR, "agent_state")

_lock = threading.Lock()


def ensure_dirs():
    os.makedirs(STATE_DIR, exist_ok=True)
    return STATE_DIR


def path_for(site_key: str, name: str) -> str:
    ensure_dirs()
    return os.path.join(STATE_DIR, f"{site_key}-{name}.json")


def load(site_key: str, name: str, default):
    p = path_for(site_key, name)
    if not os.path.exists(p):
        return default
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[store] no se pudo leer {p}: {e} — se usa el default")
        return default


def save(site_key: str, name: str, data):
    """Escritura atomica: se escribe a un temporal y se reemplaza, para que un
    corte a media escritura no deje el indice corrupto."""
    p = path_for(site_key, name)
    with _lock:
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, p)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
    return p


def is_persistent() -> bool:
    """True si DATA_DIR se configuro explicitamente (volumen). Si no, el estado
    es efimero y hay que avisarlo fuerte."""
    return bool(os.getenv("DATA_DIR"))
