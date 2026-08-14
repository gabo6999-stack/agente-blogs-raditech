import re
import unicodedata
import requests
from config import UNSPLASH_ACCESS_KEY


def _ascii_slug(text: str, fallback: str = "unsplash") -> str:
    """Slug ASCII seguro para headers HTTP (Content-Disposition es latin-1).
    Nombres de fotógrafos con caracteres no-latin1 (ż, ı, ø...) rompían la subida."""
    normalized = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return slug or fallback


def get_unsplash_image(query: str, skip_ids: set = None, per_page: int = 10) -> dict | None:
    """
    Busca una imagen en Unsplash relacionada con el query.
    Retorna dict con url, photographer y attribution.

    `skip_ids` permite pedir otra foto cuando la compuerta 2 rechaza la primera por
    repetida: se salta cualquier id de Unsplash ya usado en ese sitio.
    """
    skip_ids = skip_ids or set()
    try:
        url = "https://api.unsplash.com/search/photos"
        params = {
            "query": query,
            "per_page": per_page,
            "orientation": "landscape",
            "content_filter": "high"
        }
        headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}

        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("results"):
            print(f"[Images] No se encontraron imágenes para: {query}")
            return None

        candidatos = [p for p in data["results"] if p.get("id") not in skip_ids]
        if not candidatos:
            print(f"[Images] Las {len(data['results'])} fotos de '{query}' ya se usaron en este sitio")
            return None
        photo = candidatos[0]

        # Trigger download (requerido por Unsplash API guidelines)
        download_url = photo["links"]["download_location"]
        requests.get(
            download_url,
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            timeout=10
        )

        return {
            "unsplash_id": photo.get("id", ""),
            "url": photo["urls"]["regular"],
            "full_url": photo["urls"]["full"],
            "thumb_url": photo["urls"]["small"],
            "photographer": photo["user"]["name"],
            "photographer_url": photo["user"]["links"]["html"],
            "unsplash_url": photo["links"]["html"],
            "alt_text": photo.get("alt_description", query),
            "width": photo["width"],
            "height": photo["height"]
        }

    except Exception as e:
        print(f"[Images] Error obteniendo imagen de Unsplash: {e}")
        return None


def build_alt_text(image_data: dict, focus_keyword: str, topic: str = "") -> str:
    """Alt descriptivo que incluye la keyword objetivo de forma natural.

    La compuerta 2 exige que el alt lleve la keyword. El alt que devuelve Unsplash
    describe la foto, no el artículo, así que se antepone la keyword.
    """
    base = (image_data.get("alt_text") or topic or "").strip().rstrip(".")
    kw = (focus_keyword or "").strip()
    if not kw:
        return base[:120]
    if kw.lower() in base.lower():
        return base[:120]
    return (f"{kw} — {base}" if base else kw)[:120]


def download_image(image_data: dict) -> bytes | None:
    """Descarga los bytes de la foto. Se descarga ANTES de subir para poder
    calcular el SHA-256 y consultarlo contra el registro de imágenes del sitio."""
    try:
        r = requests.get(image_data["url"], timeout=40)
        r.raise_for_status()
        return r.content
    except Exception as e:
        print(f"[Images] Error descargando la imagen: {e}")
        return None


def upload_bytes_to_wordpress(image_bytes: bytes, filename: str, alt_text: str,
                              wp_url: str, headers: dict) -> int | None:
    """Sube bytes ya descargados y fija el alt. Devuelve el media_id."""
    try:
        media_url = f"{wp_url}/wp-json/wp/v2/media"
        media_headers = {
            **headers,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "image/jpeg",
        }
        r = requests.post(media_url, headers=media_headers, data=image_bytes, timeout=60)
        r.raise_for_status()
        media_id = r.json()["id"]
        requests.post(f"{media_url}/{media_id}", headers=headers,
                      json={"alt_text": alt_text}, timeout=20)
        print(f"[Images] Imagen subida a WordPress, ID: {media_id} (alt: {alt_text!r})")
        return media_id
    except Exception as e:
        print(f"[Images] Error subiendo imagen: {e}")
        return None


def upload_image_to_wordpress(image_data: dict, wp_url: str, headers: dict) -> int | None:
    """
    Descarga la imagen de Unsplash y la sube a WordPress Media Library.
    Retorna el media_id o None si falla.
    """
    try:
        # Descargar imagen
        img_response = requests.get(image_data["url"], timeout=30)
        img_response.raise_for_status()

        # Subir a WordPress
        media_url = f"{wp_url}/wp-json/wp/v2/media"
        filename = f"blog-image-{_ascii_slug(image_data.get('photographer', ''))}.jpg"

        media_headers = {
            **headers,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "image/jpeg"
        }

        media_response = requests.post(
            media_url,
            headers=media_headers,
            data=img_response.content,
            timeout=30
        )
        media_response.raise_for_status()
        media_id = media_response.json()["id"]

        # Actualizar alt text
        requests.post(
            f"{media_url}/{media_id}",
            headers=headers,
            json={"alt_text": image_data["alt_text"]},
            timeout=10
        )

        print(f"[Images] Imagen subida a WordPress, ID: {media_id}")
        return media_id

    except Exception as e:
        print(f"[Images] Error subiendo imagen a WordPress: {e}")
        return None
