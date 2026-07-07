import requests
from requests.auth import HTTPBasicAuth
from config import SITES


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


def publish_post(site_key: str, blog_data: dict, featured_media_id: int = None) -> dict | None:
    """
    Publica el post en WordPress con metadatos de Rank Math.
    Retorna el post creado o None si falla.
    """
    wp_url, headers = get_wp_headers(site_key)

    # Agregar atribución de Unsplash al final del contenido si hay imagen
    content = blog_data.get("content", "")

    payload = {
        "title": blog_data["title"],
        "slug": blog_data.get("slug", ""),
        "content": content,
        "excerpt": blog_data.get("excerpt", ""),
        "status": "publish",
        "meta": {
            "rank_math_title": blog_data.get("rank_math_title", blog_data["title"]),
            "rank_math_description": blog_data.get("rank_math_description", ""),
            "rank_math_focus_keyword": blog_data.get("rank_math_focus_keyword", ""),
        }
    }

    # Agregar imagen destacada si existe
    if featured_media_id:
        payload["featured_media"] = featured_media_id

    # Asignar categoría detectada por Claude o fallback del config
    from config import SITES
    category_name = blog_data.get("category") or SITES[site_key].get("category", "Tecnología Médica")
    cat_id = get_or_create_category(wp_url, headers, category_name)
    if cat_id:
        payload["categories"] = [cat_id]

    # Agregar tags si existen
    tags = blog_data.get("tags", [])
    if tags:
        tag_ids = get_or_create_tags(wp_url, headers, tags)
        if tag_ids:
            payload["tags"] = tag_ids

    try:
        response = requests.post(
            f"{wp_url}/wp-json/wp/v2/posts",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        post = response.json()
        print(f"[WP] Post publicado: {post['link']}")

        # PATCH separado para rank_math — Rank Math no acepta meta en el POST inicial
        rank_meta = {
            "meta": {
                "rank_math_title": blog_data.get("rank_math_title", blog_data["title"]),
                "rank_math_description": blog_data.get("rank_math_description", ""),
                "rank_math_focus_keyword": blog_data.get("rank_math_focus_keyword", ""),
            }
        }
        patch = requests.patch(
            f"{wp_url}/wp-json/wp/v2/posts/{post['id']}",
            headers=headers,
            json=rank_meta,
            timeout=15
        )
        if patch.status_code == 200:
            print(f"[WP] Rank Math meta guardado en post {post['id']}")
        else:
            print(f"[WP] Advertencia: rank_math meta no guardado ({patch.status_code})")

        # Persistencia fiable de rank_math vía endpoint propio de Rank Math
        set_rankmath_meta(wp_url, headers, post["id"], blog_data)

        return post

    except Exception as e:
        print(f"[WP] Error publicando post: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[WP] Respuesta: {e.response.text[:500]}")
        return None


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


def get_or_create_category(wp_url: str, headers: dict, category_name: str) -> int | None:
    try:
        search = requests.get(
            f"{wp_url}/wp-json/wp/v2/categories",
            headers=headers,
            params={"search": category_name},
            timeout=10
        )
        results = search.json()
        if results:
            return results[0]["id"]
        create = requests.post(
            f"{wp_url}/wp-json/wp/v2/categories",
            headers=headers,
            json={"name": category_name, "slug": category_name.lower().replace(" ", "-")},
            timeout=10
        )
        if create.status_code == 201:
            cat_id = create.json()["id"]
            print(f"[WP] Categoría creada: '{category_name}' (ID {cat_id})")
            return cat_id
    except Exception as e:
        print(f"[WP] Error con categoría '{category_name}': {e}")
    return None


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
