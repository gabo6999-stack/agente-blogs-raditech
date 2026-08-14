"""Registro de imagenes usadas por sitio (compuerta 2).

Tres indices, porque el hash solo no basta: Unsplash sirve el mismo recurso con
distinto nombre y a veces recomprimido, asi que un byte distinto cambia el
SHA-256. Se guarda tambien nombre de archivo y dimensiones para cazar re-subidas
del mismo recurso con otro nombre.
"""
import hashlib

from tools import store

NAME = "image-registry"


def _empty():
    return {"by_hash": {}, "by_filename": {}, "by_dims": {}, "by_unsplash_id": {}}


def load(site_key: str) -> dict:
    reg = store.load(site_key, NAME, _empty())
    for k in _empty():
        reg.setdefault(k, {})
    return reg


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(site_key: str, image_bytes: bytes, filename: str = "",
          width: int = None, height: int = None, unsplash_id: str = "") -> dict:
    """Devuelve {'duplicate': bool, 'reason': str, 'match': ...} SIN registrar."""
    reg = load(site_key)
    h = sha256(image_bytes)

    if h in reg["by_hash"]:
        return {"duplicate": True, "hash": h,
                "reason": f"SHA-256 identico a la imagen del post {reg['by_hash'][h].get('post_id')}",
                "match": reg["by_hash"][h]}

    if unsplash_id and unsplash_id in reg["by_unsplash_id"]:
        return {"duplicate": True, "hash": h,
                "reason": f"mismo recurso de Unsplash ({unsplash_id}) ya usado en el post "
                          f"{reg['by_unsplash_id'][unsplash_id].get('post_id')}",
                "match": reg["by_unsplash_id"][unsplash_id]}

    if filename and filename in reg["by_filename"]:
        return {"duplicate": True, "hash": h,
                "reason": f"nombre de archivo repetido ({filename})",
                "match": reg["by_filename"][filename]}

    dims = f"{width}x{height}" if width and height else None
    if dims and dims in reg["by_dims"]:
        prev = reg["by_dims"][dims]
        # mismas dimensiones + mismo tamaño en bytes ~ misma foto recomprimida
        if abs(prev.get("bytes", 0) - len(image_bytes)) < 1024:
            return {"duplicate": True, "hash": h,
                    "reason": f"mismas dimensiones ({dims}) y tamaño casi identico al del post "
                              f"{prev.get('post_id')} — probable re-subida del mismo recurso",
                    "match": prev}

    return {"duplicate": False, "hash": h, "reason": "", "match": None}


def register(site_key: str, image_bytes: bytes, filename: str = "", width: int = None,
             height: int = None, unsplash_id: str = "", post_id: int = None,
             media_id: int = None, url: str = "") -> dict:
    reg = load(site_key)
    h = sha256(image_bytes)
    entry = {"hash": h, "filename": filename, "width": width, "height": height,
             "bytes": len(image_bytes), "unsplash_id": unsplash_id,
             "post_id": post_id, "media_id": media_id, "url": url}
    reg["by_hash"][h] = entry
    if filename:
        reg["by_filename"][filename] = entry
    if width and height:
        reg["by_dims"][f"{width}x{height}"] = entry
    if unsplash_id:
        reg["by_unsplash_id"][unsplash_id] = entry
    store.save(site_key, NAME, reg)
    return entry


def count(site_key: str) -> int:
    return len(load(site_key)["by_hash"])
