import html
import re
import uuid
import requests
from requests.auth import HTTPBasicAuth
from config import SITES
from tools.faq_schema import extract_visible_faq


def get_wp_headers(site_key: str) -> tuple[str, dict]:
    """
    Retorna la URL base y headers de autenticación para WordPress.
    """
    site = SITES[site_key]
    wp_url = site["wp_url"]
    
    # Autenticación básica (funciona con Application Passwords de WP)
    auth = HTTPBasicAuth(site["wp_user"], site["wp_password"])
    
    # Obtener JWT token
    token_response = requests.post(
        f"{wp_url}/wp-json/jwt-auth/v1/token",
        json={
            "username": site["wp_user"],
            "password": site["wp_password"]
        },
        timeout=15
    )
    
    if token_response.status_code == 200:
        token = token_response.json().get("token")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    else:
        # Fallback a Basic Auth si JWT falla
        print("[WP] JWT falló, usando Basic Auth")
        import base64
        credentials = base64.b64encode(
            f"{site['wp_user']}:{site['wp_password']}".encode()
        ).decode()
        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json"
        }
    
    return wp_url, headers


def set_rankmath_meta(wp_url: str, headers: dict, post_id: int, blog_data: dict) -> bool:
    """
    Persiste el meta de Rank Math vía su endpoint propio (rankmath/v1/updateMeta).
    El campo `meta` de /wp/v2 NO persiste rank_math_* (Rank Math lo ignora en silencio),
    por eso usamos este endpoint. Requiere que el usuario autenticado tenga edit_post.
    """
    meta = {
        "rank_math_title": blog_data.get("rank_math_title", blog_data.get("title", "")),
        "rank_math_description": blog_data.get("rank_math_description", ""),
        "rank_math_focus_keyword": blog_data.get("rank_math_focus_keyword", ""),
    }
    try:
        r = requests.post(
            f"{wp_url}/wp-json/rankmath/v1/updateMeta",
            headers=headers,
            json={"objectID": post_id, "objectType": "post", "meta": meta},
            timeout=15,
        )
        if r.status_code == 200:
            print(f"[WP] Rank Math meta (updateMeta) guardado en post {post_id}")
            return True
        print(f"[WP] updateMeta no disponible ({r.status_code}); se dejó el PATCH estándar")
    except Exception as e:
        print(f"[WP] Error en updateMeta: {e}")
    return False


def set_faq_schema_meta(site_key: str, post_id: int, content: str) -> dict:
    """Persiste el FAQPage schema en Rank Math (meta `rank_math_schema_FAQPage`)
    vía rankmath/v1/updateMeta, leyendo la FAQ VISIBLE del content.

    Por qué: en sitios cuya cuenta publicadora es 'author' (sin unfiltered_html,
    p.ej. CMLC/pedrogavito), WordPress BORRA el <script> ld+json del content al
    guardar (wp_kses_post), así que embeberlo no sirve. Rank Math, en cambio,
    emite el schema en el @graph del <head> a partir de este meta, inmune a kses.
    Tras guardarlo se re-guarda el post para forzar el purge de LiteSpeed
    (Hostinger cachea el HTML). Se activa por sitio con el flag
    SITES[site_key]["faq_schema_via_meta"] = True.
    """
    faqs = extract_visible_faq(content or "")
    if not faqs:
        print(f"[FAQ schema] {site_key} #{post_id}: sin FAQ visible, se omite")
        return {"skipped": "sin FAQ visible"}
    wp_url, headers = get_wp_headers(site_key)
    faq_value = {
        "@type": "FAQPage",
        "metadata": {
            "title": "FAQ",
            "type": "template",
            "shortcode": f"s-{uuid.uuid4().hex[:13]}",
            "isPrimary": 0,
            "reviewLocation": "custom",
        },
        "mainEntity": [
            {"@type": "Question", "name": f["question"],
             "acceptedAnswer": {"@type": "Answer", "text": f["answer"]}}
            for f in faqs
        ],
    }
    try:
        r = requests.post(
            f"{wp_url}/wp-json/rankmath/v1/updateMeta",
            headers=headers,
            json={"objectID": int(post_id), "objectType": "post",
                  "meta": {"rank_math_schema_FAQPage": faq_value}},
            timeout=20,
        )
        ok = r.status_code == 200
        print(f"[FAQ schema] {site_key} #{post_id}: updateMeta {r.status_code} "
              f"({len(faqs)} preguntas)")
        # Purga de LiteSpeed: re-guardar el post dispara purge-on-update para que
        # el HTML cacheado se regenere ya con el schema en el <head>.
        try:
            requests.post(
                f"{wp_url}/wp-json/wp/v2/posts/{int(post_id)}",
                headers=headers, json={"content": content}, timeout=20,
            )
        except Exception as e:
            print(f"[FAQ schema] purge re-save no crítico falló: {e}")
        return {"ok": ok, "status": r.status_code, "questions": len(faqs)}
    except Exception as e:
        print(f"[FAQ schema] {site_key} #{post_id}: error {e}")
        return {"error": str(e)}


def create_draft(site_key: str, blog_data: dict, featured_media_id: int = None) -> dict:
    """Crea el post como BORRADOR. Nunca publica.

    Publicar es un paso aparte (`promote_to_publish`) que solo ocurre si las diez
    compuertas pasan. El motivo es que la compuerta 1 necesita que el post exista
    en WordPress para poder abrirlo en el editor y leer la puntuación real de Rank
    Math, y la compuerta 4 necesita ver el slug que WordPress asignó de verdad.

    Devuelve {'post': dict|None, 'error': str, 'category_error': str}.
    """
    wp_url, headers = get_wp_headers(site_key)
    site = SITES[site_key]

    payload = {
        "title": blog_data["title"],
        "slug": blog_data.get("slug", ""),
        "content": blog_data.get("content", ""),
        "excerpt": blog_data.get("excerpt", ""),
        "status": "draft",
        "meta": {
            "rank_math_title": blog_data.get("rank_math_title", blog_data["title"]),
            "rank_math_description": blog_data.get("rank_math_description", ""),
            "rank_math_focus_keyword": blog_data.get("rank_math_focus_keyword", ""),
        },
    }
    if featured_media_id:
        payload["featured_media"] = featured_media_id

    category_name = blog_data.get("category") or site.get("category", "")
    cat_id, cat_error = resolve_category(wp_url, headers, category_name, site_key)
    if cat_id:
        payload["categories"] = [cat_id]
    else:
        print(f"[WP] Categoría sin resolver: {cat_error}")

    tags = blog_data.get("tags", [])
    if tags:
        tag_ids = get_or_create_tags(wp_url, headers, tags)
        if tag_ids:
            payload["tags"] = tag_ids

    try:
        r = requests.post(f"{wp_url}/wp-json/wp/v2/posts", headers=headers,
                          json=payload, timeout=40)
        r.raise_for_status()
        post = r.json()
        print(f"[WP] Borrador creado #{post['id']} slug='{post.get('slug')}'")

        set_rankmath_meta(wp_url, headers, post["id"], blog_data)
        return {"post": post, "error": "", "category_error": cat_error}
    except Exception as e:
        detalle = ""
        if hasattr(e, "response") and e.response is not None:
            detalle = e.response.text[:500]
        print(f"[WP] Error creando borrador: {e} {detalle}")
        return {"post": None, "error": f"{e} {detalle}".strip(), "category_error": cat_error}


def promote_to_publish(site_key: str, post_id: int) -> dict | None:
    """Pasa un borrador ya validado a publicado."""
    wp_url, headers = get_wp_headers(site_key)
    try:
        r = requests.post(f"{wp_url}/wp-json/wp/v2/posts/{post_id}", headers=headers,
                          json={"status": "publish"}, timeout=40)
        r.raise_for_status()
        post = r.json()
        print(f"[WP] Publicado #{post_id}: {post.get('link')}")
        return post
    except Exception as e:
        print(f"[WP] Error publicando #{post_id}: {e}")
        return None


def update_draft(site_key: str, post_id: int, blog_data: dict) -> dict | None:
    """Actualiza el contenido de un borrador (usado al iterar por puntuación)."""
    wp_url, headers = get_wp_headers(site_key)
    payload = {"content": blog_data.get("content", "")}
    for campo, clave in (("title", "title"), ("excerpt", "excerpt")):
        if blog_data.get(clave):
            payload[campo] = blog_data[clave]
    payload["meta"] = {
        "rank_math_title": blog_data.get("rank_math_title", ""),
        "rank_math_description": blog_data.get("rank_math_description", ""),
        "rank_math_focus_keyword": blog_data.get("rank_math_focus_keyword", ""),
    }
    try:
        r = requests.post(f"{wp_url}/wp-json/wp/v2/posts/{post_id}", headers=headers,
                          json=payload, timeout=40)
        r.raise_for_status()
        set_rankmath_meta(wp_url, headers, post_id, blog_data)
        return r.json()
    except Exception as e:
        print(f"[WP] Error actualizando borrador #{post_id}: {e}")
        return None


def get_media_info(site_key: str, media_id: int) -> dict:
    """Datos de la imagen para la compuerta 2: alt, URLs de thumbnail y medium."""
    wp_url, headers = get_wp_headers(site_key)
    try:
        r = requests.get(f"{wp_url}/wp-json/wp/v2/media/{media_id}", headers=headers,
                         params={"context": "edit"}, timeout=25)
        r.raise_for_status()
        m = r.json()
        sizes = (m.get("media_details") or {}).get("sizes", {})
        return {
            "media_id": media_id,
            "alt_text": m.get("alt_text", ""),
            "source_url": m.get("source_url", ""),
            "width": (m.get("media_details") or {}).get("width"),
            "height": (m.get("media_details") or {}).get("height"),
            "filename": (m.get("media_details") or {}).get("file", "").split("/")[-1],
            "sizes": {k: v.get("source_url") for k, v in sizes.items()},
        }
    except Exception as e:
        print(f"[WP] Error leyendo media {media_id}: {e}")
        return {"media_id": media_id, "alt_text": "", "sizes": {}}


def set_media_alt(site_key: str, media_id: int, alt_text: str) -> bool:
    wp_url, headers = get_wp_headers(site_key)
    try:
        r = requests.post(f"{wp_url}/wp-json/wp/v2/media/{media_id}", headers=headers,
                          json={"alt_text": alt_text}, timeout=20)
        return r.status_code == 200
    except Exception:
        return False


def trash_post(site_key: str, post_id: int) -> bool:
    """Manda el borrador a la papelera. Se usa solo cuando la compuerta 4 detecta
    que WordPress asignó un slug con sufijo -N (el contenido ya existía)."""
    wp_url, headers = get_wp_headers(site_key)
    try:
        r = requests.delete(f"{wp_url}/wp-json/wp/v2/posts/{post_id}", headers=headers,
                            timeout=25)
        return r.status_code == 200
    except Exception as e:
        print(f"[WP] Error mandando #{post_id} a la papelera: {e}")
        return False


def fetch_posts_for_index(site_key: str) -> list[dict]:
    """Baja todos los posts (publicados, borradores y programados) con lo que el
    índice anti-duplicados necesita: título, H1 del cuerpo, focus keyword y H2.

    Se incluyen borradores y programados a propósito: un borrador ya ocupa el tema
    y su slug. Auditar solo con status=publish deja escapar lo programado.
    """
    from tools.html_tools import analyze, normalize_text
    from tools.topic_index import normalize_title

    wp_url, headers = get_wp_headers(site_key)
    out, page = [], 1
    while True:
        r = requests.get(f"{wp_url}/wp-json/wp/v2/posts", headers=headers,
                         params={"context": "edit", "per_page": 100, "page": page,
                                 "status": "publish,draft,future,pending,private",
                                 "orderby": "date", "order": "asc"},
                         timeout=45)
        if r.status_code != 200:
            print(f"[WP] fetch_posts_for_index página {page}: HTTP {r.status_code}")
            break
        batch = r.json()
        if not batch:
            break
        for p in batch:
            content = (p.get("content") or {}).get("raw", "") or ""
            title = (p.get("title") or {}).get("raw") or (p.get("title") or {}).get("rendered", "")
            a = analyze(content)
            h1 = next((t for lvl, t in a["headings"] if lvl == 1), "")
            meta = p.get("meta") or {}
            out.append({
                "id": p["id"],
                "slug": p.get("slug"),
                "title": normalize_text(title),
                "norm_title": normalize_title(title),
                "h1": h1,
                "focus_keyword": meta.get("rank_math_focus_keyword", ""),
                "seo_score": meta.get("rank_math_seo_score", ""),
                "h2": a["h2_texts"],
                "norm_h2": sorted({normalize_title(h) for h in a["h2_texts"] if normalize_title(h)}),
                "status": p.get("status"),
                "link": p.get("link"),
                "date_gmt": p.get("date_gmt"),
            })
        if len(batch) < 100:
            break
        page += 1
    return out


def published_dates(site_key: str) -> list[str]:
    """Fechas date_gmt de los posts PUBLICADOS. Fuente de verdad para el ritmo de
    publicación: se lee de WordPress, no de un log local que se pierde al redeplegar."""
    wp_url, headers = get_wp_headers(site_key)
    fechas, page = [], 1
    while True:
        r = requests.get(f"{wp_url}/wp-json/wp/v2/posts", headers=headers,
                         params={"per_page": 100, "page": page, "status": "publish",
                                 "orderby": "date", "order": "desc"}, timeout=40)
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        fechas.extend(p.get("date_gmt") for p in batch)
        if len(batch) < 100 or len(fechas) >= 200:
            break
        page += 1
    return [f for f in fechas if f]


def get_posts_list(site_key: str, per_page: int = 100) -> list[dict]:
    """
    Retorna lista de posts publicados: id, title, url.
    """
    wp_url, headers = get_wp_headers(site_key)
    try:
        response = requests.get(
            f"{wp_url}/wp-json/wp/v2/posts",
            headers=headers,
            params={"per_page": per_page, "orderby": "date", "order": "desc", "status": "publish"},
            timeout=15
        )
        response.raise_for_status()
        return [
            {"id": p["id"], "title": p["title"]["rendered"], "url": p["link"]}
            for p in response.json()
        ]
    except Exception as e:
        print(f"[WP] Error obteniendo lista de posts: {e}")
        return []


def get_post(site_key: str, post_id: int) -> dict | None:
    """
    Obtiene un post existente de WordPress por ID.
    Retorna el post raw o None si falla.
    """
    wp_url, headers = get_wp_headers(site_key)
    try:
        response = requests.get(
            f"{wp_url}/wp-json/wp/v2/posts/{post_id}",
            headers=headers,
            params={"context": "edit"},
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[WP] Error obteniendo post {post_id}: {e}")
        return None


def get_tag_names(site_key: str, tag_ids: list[int]) -> list[str]:
    """
    Convierte una lista de IDs de tags a nombres.
    """
    if not tag_ids:
        return []
    wp_url, headers = get_wp_headers(site_key)
    try:
        response = requests.get(
            f"{wp_url}/wp-json/wp/v2/tags",
            headers=headers,
            params={"include": ",".join(map(str, tag_ids)), "per_page": 100},
            timeout=10
        )
        if response.status_code == 200:
            return [t["name"] for t in response.json()]
    except Exception as e:
        print(f"[WP] Error obteniendo nombres de tags: {e}")
    return []


def set_featured_image(site_key: str, post_id: int, featured_media_id: int) -> dict | None:
    """
    Actualiza solo la imagen destacada de un post existente.
    """
    wp_url, headers = get_wp_headers(site_key)
    try:
        response = requests.put(
            f"{wp_url}/wp-json/wp/v2/posts/{post_id}",
            headers=headers,
            json={"featured_media": featured_media_id},
            timeout=30
        )
        response.raise_for_status()
        post = response.json()
        print(f"[WP] Imagen actualizada en post: {post['link']}")
        return post
    except Exception as e:
        print(f"[WP] Error actualizando imagen: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[WP] Respuesta: {e.response.text[:500]}")
        return None


def update_post(site_key: str, post_id: int, blog_data: dict, featured_media_id: int = None) -> dict | None:
    """
    Actualiza un post existente en WordPress con los campos proporcionados.
    Retorna el post actualizado o None si falla.
    """
    wp_url, headers = get_wp_headers(site_key)

    payload = {
        "title": blog_data["title"],
        "content": blog_data.get("content", ""),
        "excerpt": blog_data.get("excerpt", ""),
        "meta": {
            "rank_math_title": blog_data.get("rank_math_title", ""),
            "rank_math_description": blog_data.get("rank_math_description", ""),
            "rank_math_focus_keyword": blog_data.get("rank_math_focus_keyword", ""),
        }
    }

    if featured_media_id:
        payload["featured_media"] = featured_media_id

    tags = blog_data.get("tags", [])
    if tags:
        tag_ids = get_or_create_tags(wp_url, headers, tags)
        if tag_ids:
            payload["tags"] = tag_ids

    try:
        response = requests.put(
            f"{wp_url}/wp-json/wp/v2/posts/{post_id}",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        post = response.json()
        print(f"[WP] Post actualizado: {post['link']}")
        set_rankmath_meta(wp_url, headers, post_id, blog_data)
        return post
    except Exception as e:
        print(f"[WP] Error actualizando post: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[WP] Respuesta: {e.response.text[:500]}")
        return None


def list_categories(site_key: str = None, wp_url: str = None, headers: dict = None) -> dict:
    """Todas las categorías del sitio: {id: nombre_decodificado}.

    Se decodifican las entidades HTML porque WordPress guarda el nombre YA
    codificado: la categoría 22 se llama literalmente 'HOA &amp; Condo Accounting'
    en la base de datos.
    """
    if wp_url is None or headers is None:
        wp_url, headers = get_wp_headers(site_key)
    out, page = {}, 1
    while True:
        r = requests.get(f"{wp_url}/wp-json/wp/v2/categories", headers=headers,
                         params={"per_page": 100, "page": page, "hide_empty": "false"},
                         timeout=20)
        if r.status_code != 200:
            print(f"[WP] Error listando categorías ({r.status_code})")
            break
        batch = r.json()
        if not batch:
            break
        for c in batch:
            out[c["id"]] = html.unescape(c["name"])
        if len(batch) < 100:
            break
        page += 1
    return out


def resolve_category(wp_url: str, headers: dict, category_name: str,
                     site_key: str = None) -> tuple[int | None, str]:
    """Busca la categoría por nombre SIN crearla. Devuelve (id, motivo_si_falla).

    Por qué ya no usa ?search= ni crea nada. Medición literal del 14-ago-2026
    contra propertyledger.us:

        GET /wp/v2/categories?search=HOA & Condo Accounting      -> []
        GET /wp/v2/categories?search=HOA &amp; Condo Accounting  -> [(22, 'HOA &amp; Condo Accounting')]

    El nombre vive HTML-codificado en la base. La versión anterior buscaba con el
    '&' literal, no encontraba nada, intentaba CREAR una categoría que ya existía,
    WordPress respondía term_exists (no 201), la función devolvía None, el payload
    salía sin `categories` y WordPress caía al default: Uncategorized. Es lo que le
    pasó al post #322 del 13-ago.

    Además, la compuerta 6 prohíbe crear categorías nuevas sin aprobación: si el
    tema no encaja en ninguna existente, se reporta y el post se queda en borrador.
    """
    cats = list_categories(wp_url=wp_url, headers=headers)
    quiero = _norm_cat(category_name)

    for cid, nombre in cats.items():
        if _norm_cat(nombre) == quiero:
            return cid, ""
    # tolerancia: coincidencia por contención (p.ej. "HOA Accounting" -> "HOA & Condo Accounting")
    candidatos = [(cid, n) for cid, n in cats.items()
                  if _norm_cat(n) != "uncategorized" and
                  (quiero in _norm_cat(n) or _norm_cat(n) in quiero)]
    if len(candidatos) == 1:
        print(f"[WP] Categoría '{category_name}' resuelta por coincidencia parcial "
              f"-> '{candidatos[0][1]}' (id {candidatos[0][0]})")
        return candidatos[0][0], ""

    return None, (f"'{category_name}' no existe en el sitio. Categorías reales: "
                  f"{sorted(n for n in cats.values())}. No se crea ninguna sin aprobación")


def _norm_cat(name: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(name or "").replace("&", "and")).strip().lower()


def get_or_create_tags(wp_url: str, headers: dict, tag_names: list[str]) -> list[int]:
    """
    Obtiene o crea tags en WordPress. Retorna lista de IDs.
    """
    tag_ids = []
    
    for tag_name in tag_names:
        try:
            # Buscar si ya existe
            search = requests.get(
                f"{wp_url}/wp-json/wp/v2/tags",
                headers=headers,
                params={"search": tag_name},
                timeout=10
            )
            results = search.json()
            
            if results:
                tag_ids.append(results[0]["id"])
            else:
                # Crear nuevo tag
                create = requests.post(
                    f"{wp_url}/wp-json/wp/v2/tags",
                    headers=headers,
                    json={"name": tag_name},
                    timeout=10
                )
                if create.status_code == 201:
                    tag_ids.append(create.json()["id"])
        except Exception as e:
            print(f"[WP] Error con tag '{tag_name}': {e}")
    
    return tag_ids
