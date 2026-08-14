"""Pipeline con compuertas: borrador -> validar -> publicar.

Sustituye al flujo anterior, que generaba el artículo y lo mandaba a WordPress con
`status: "publish"` de una vez, sin ninguna validación. La misión del agente no es
publicar: es publicar solo lo que está listo para rankear. Si alguna compuerta
falla, el post se queda en BORRADOR y se reporta por qué.

Orden de ejecución:

     0  salud del sitio            (5 URLs, sin caché, UA Googlebot)
    10  ritmo de publicación       (máx 2/día, mín 4h, parada ante ráfaga)
     3  duplicado por tema         (antes de escribir nada)
        --- generación + saneado ---
     5  un solo H1                 7  HTML válido        8  metadata Rank Math
     4  slug limpio                9  enlaces internos verificados
     2  imagen destacada única
        --- se crea el BORRADOR en WordPress ---
     4  slug real devuelto por WP  6  categoría asignada de verdad
     1  puntuación Rank Math leída del editor (con hasta 3 iteraciones)
        --- solo entonces se publica ---
        verificación posterior + reporte
"""
import os
import traceback
from datetime import datetime, timezone

from config import SITES
from gates import GateReport, GateResult
from gates.cadence import g10_publish_rate, is_halted
from gates.content import g05_single_h1, g07_valid_html
from gates.links import g09_internal_links
from gates.media import g02_featured_image
from gates.rankmath import g01_prefilter, g01_real_score, necesita_iterar
from gates.seo import g03_no_duplicate_topic, g04_clean_slug, g08_rankmath_meta
from gates.taxonomy import g06_category
from tools import image_registry, report as report_mod, site_health, store, topic_index
from tools.html_tools import sanitize
from tools.images import (build_alt_text, download_image, get_unsplash_image,
                          upload_bytes_to_wordpress)
from tools.wordpress import (create_draft, get_media_info, get_wp_headers,
                             list_categories, promote_to_publish, published_dates,
                             set_media_alt, trash_post, update_draft)

MAX_ITERACIONES_SCORE = 3


def _service_pages(site_key: str) -> list:
    """Páginas de servicio del sitio (no artículos de blog), para la compuerta 9c."""
    links = (SITES[site_key].get("prompt_profile") or {}).get("internal_links", {})
    base = SITES[site_key]["wp_url"].rstrip("/")
    fuera = ("/blog/", "-guide", "-basics", "-explained")
    return [u for u in links
            if u.rstrip("/") == base or not any(f in u for f in fuera)]


def run_guarded_pipeline(site_key: str, topic: str = None, *, dry_run: bool = False,
                         headless: bool = True) -> dict:
    """Devuelve el reporte. `dry_run=True` se detiene antes de crear el borrador."""
    inicio = datetime.now(timezone.utc)
    rep = GateReport(site_key, topic or "")
    site = SITES[site_key]
    site_url = site["wp_url"].rstrip("/")
    blog_data, post, media_info, links_diag = {}, None, {}, None
    score, screenshot, intentos = None, None, 0
    health = None

    if not store.is_persistent():
        print("[AVISO] DATA_DIR no está configurado: el índice de temas y el registro "
              "de imágenes son EFÍMEROS y se perderán al redesplegar. Montar un volumen "
              "y exportar DATA_DIR=/data.")

    def salir(publicado=False):
        r = report_mod.build(site_key, topic or "", rep, blog_data=blog_data, post=post,
                             publicado=publicado, score=score, screenshot=screenshot,
                             health=health, links=links_diag, image=media_info,
                             intentos=intentos or 1,
                             postcheck=locals().get("postcheck"))
        r["duracion_s"] = round((datetime.now(timezone.utc) - inicio).total_seconds())
        report_mod.save(r)
        print(f"\n[pipeline] {rep.summary()} — "
              f"{'PUBLICADO' if publicado else 'SE QUEDA EN BORRADOR'}")
        return r

    try:
        # ── 0. Salud del sitio ───────────────────────────────────────────────
        print("\n[0/10] Salud del sitio")
        health = site_health.check(site_key)
        rep.add(GateResult(
            "G00", "Salud del sitio antes de publicar", passed=health["ok"],
            reason="; ".join(health["motivos"]) or
                   f"latencia mediana {health['mediana_ms']} ms, códigos {health['codigos']}",
            details=health))
        if not health["ok"]:
            return salir()

        # ── 10. Ritmo ────────────────────────────────────────────────────────
        print("\n[10] Ritmo de publicación")
        if is_halted(site_key):
            rep.extend(g10_publish_rate(site_key, []))
            return salir()
        fechas = published_dates(site_key)
        rep.extend(g10_publish_rate(site_key, fechas))
        if not rep.ok:
            return salir()

        # ── Tema ─────────────────────────────────────────────────────────────
        print("\n[tema] Refrescando el índice de temas publicados")
        topic_index.refresh(site_key)
        if not topic:
            from tools.logger import get_used_topics
            from tools.trends import pick_topic
            topic = pick_topic(site_key, get_used_topics(site_key))
        rep.topic = topic
        print(f"[tema] {topic}")

        # ── 3. Duplicado, ANTES de escribir ──────────────────────────────────
        print("\n[3] Duplicado de tema (pre-escritura)")
        previo = g03_no_duplicate_topic(site_key, topic, "", "", "")
        previo[0].gate = "G03-pre"
        previo[0].name += " (antes de escribir)"
        rep.extend(previo)
        if not rep.ok:
            return salir()

        # ── Generación ───────────────────────────────────────────────────────
        print("\n[escritura] Generando el artículo")
        from tools.writer import generate_blog
        blog_data = generate_blog(site_key, topic)

        crudo = blog_data.get("content", "")
        limpio, cambios = sanitize(crudo, blog_data.get("title", ""))
        blog_data["content"] = limpio
        rep.add(GateResult("SAN", "Saneado determinista del HTML", passed=True,
                           reason="; ".join(cambios) or "sin cambios necesarios",
                           details={"cambios": cambios,
                                    "chars_antes": len(crudo), "chars_despues": len(limpio)},
                           blocking=False))

        # ── 5, 7, 8, 4, 3 sobre el contenido generado ───────────────────────
        print("\n[5] Un solo H1  ·  [7] HTML válido")
        rep.extend(g05_single_h1(blog_data["content"]))
        rep.extend(g07_valid_html(blog_data["content"]))

        # ── Alineación de la focus keyword, ANTES de tocar WordPress ─────────
        # Es lo que más puntos mueve en Rank Math y lo que hundió a los posts del
        # agente (#318 sacó 22/100 con la keyword apareciendo cero veces en 2.349
        # palabras). Se corrige aquí, con una llamada barata a Claude, en vez de
        # descubrirlo en la compuerta 1 tras gastar una sesión de navegador.
        print("\n[kw] Alineación de la focus keyword")
        from tools.keyword_align import analizar, instrucciones
        for intento_kw in range(1, 3):
            a = analizar(blog_data)
            print(f"  '{a['keyword']}': {a['apariciones']} apariciones en {a['palabras']} "
                  f"palabras (densidad {a['densidad']}%)")
            if a["alineada"]:
                break
            for d in a["deficits"]:
                print(f"    falta: {d[:110]}")
            if intento_kw == 2:
                break
            from tools.writer import improve_blog
            mejor = improve_blog(site_key, blog_data, instrucciones(a), score_actual=None)
            if not mejor:
                break
            mejor["content"], _ = sanitize(mejor.get("content", ""), mejor.get("title", ""))
            blog_data.update(mejor)
        rep.add(GateResult(
            "KW", "Focus keyword alineada con el texto", passed=a["alineada"], blocking=False,
            reason="alineada" if a["alineada"] else "; ".join(a["deficits"])[:300],
            details=a))

        print("\n[8] Metadata de Rank Math")
        rep.extend(g08_rankmath_meta(site_key, blog_data))

        print("\n[4] Slug propuesto")
        rep.extend(g04_clean_slug(blog_data.get("slug", ""), blog_data.get("title", "")))

        print("\n[3] Duplicado de tema (post-escritura, con los H2 reales)")
        rep.extend(g03_no_duplicate_topic(
            site_key, blog_data.get("title", ""), blog_data["content"],
            blog_data.get("rank_math_focus_keyword", ""), blog_data.get("slug", "")))

        # ── 9. Enlaces ───────────────────────────────────────────────────────
        print("\n[9] Enlaces internos y externos (sin seguir redirecciones)")
        resultados, corregido, links_diag = g09_internal_links(
            blog_data["content"], site_url, _service_pages(site_key))
        if corregido != blog_data["content"]:
            blog_data["content"] = corregido
            print(f"  correcciones aplicadas: {links_diag['arreglos']}")
        rep.extend(resultados)

        if not rep.ok:
            print("\n[pipeline] Fallan compuertas previas: no se crea nada en WordPress.")
            return salir()

        # ── 2. Imagen ────────────────────────────────────────────────────────
        print("\n[2] Imagen destacada")
        media_id, image_bytes = None, None
        reg = image_registry.load(site_key)
        ya_usadas = set(reg.get("by_unsplash_id", {}).keys())
        query = blog_data.get("unsplash_query") or site.get("unsplash_fallback", topic)
        fk = blog_data.get("rank_math_focus_keyword", "")

        for intento_img in range(3):
            img = get_unsplash_image(query, skip_ids=ya_usadas)
            if not img:
                break
            image_bytes = download_image(img)
            if not image_bytes:
                break
            dup = image_registry.check(site_key, image_bytes,
                                       width=img.get("width"), height=img.get("height"),
                                       unsplash_id=img.get("unsplash_id", ""))
            if not dup["duplicate"]:
                break
            print(f"  imagen repetida ({dup['reason']}); se pide otra")
            ya_usadas.add(img.get("unsplash_id", ""))
            image_bytes = None

        if image_bytes and img:
            alt = build_alt_text(img, fk, topic)
            blog_data["_image_alt"] = alt
            from tools.images import _ascii_slug
            filename = f"{_ascii_slug(fk or topic)[:60]}.jpg"
            wp_url, headers = get_wp_headers(site_key)
            media_id = upload_bytes_to_wordpress(image_bytes, filename, alt, wp_url, headers)

        if dry_run:
            print("\n[dry-run] Se detiene antes de crear el borrador.")
            return salir()

        # ── Borrador ─────────────────────────────────────────────────────────
        print("\n[wp] Creando el BORRADOR")
        creado = create_draft(site_key, blog_data, media_id)
        post = creado["post"]
        if not post:
            rep.add(GateResult("WP", "Creación del borrador", passed=False,
                               reason=creado["error"]))
            return salir()
        if creado.get("meta_error"):
            rep.add(GateResult("WP-meta", "Metadata de Rank Math tras crear el borrador",
                               passed=False, blocking=False, reason=creado["meta_error"]))

        # ── 4. Slug REAL devuelto por WordPress ──────────────────────────────
        print("\n[4] Slug real asignado por WordPress")
        slug_real = post.get("slug", "")
        res_slug = g04_clean_slug(blog_data.get("slug", ""), blog_data.get("title", ""),
                                  wp_returned_slug=slug_real)
        for r_ in res_slug:
            r_.gate = r_.gate.replace("G04", "G04wp")
        rep.extend(res_slug)
        if any(not r_.passed and r_.blocking for r_ in res_slug):
            print(f"  WordPress asignó '{slug_real}': el contenido ya existía. "
                  f"Se manda el borrador a la papelera.")
            trash_post(site_key, post["id"])
            return salir()

        # ── 6. Categoría ─────────────────────────────────────────────────────
        print("\n[6] Categoría asignada")
        cats = list_categories(site_key)
        asignadas = [cats.get(c, str(c)) for c in post.get("categories", [])]
        res_cat = g06_category(asignadas, allowed=list(cats.values()))
        if creado.get("category_error"):
            res_cat[0].reason = (res_cat[0].reason + " | " + creado["category_error"]).strip(" |")
        rep.extend(res_cat)

        # ── 2. Imagen, comprobación completa ─────────────────────────────────
        print("\n[2] Imagen: alt, unicidad y miniaturas")
        if media_id:
            media_info = get_media_info(site_key, media_id)
            media_info["unsplash_id"] = img.get("unsplash_id", "") if img else ""
            if not media_info.get("alt_text") and blog_data.get("_image_alt"):
                set_media_alt(site_key, media_id, blog_data["_image_alt"])
                media_info["alt_text"] = blog_data["_image_alt"]
        rep.extend(g02_featured_image(site_key, media_info, fk, image_bytes))

        # ── 1. Puntuación de Rank Math ───────────────────────────────────────
        print("\n[1] Puntuación de Rank Math")
        pre, est = g01_prefilter(blog_data, site_url)
        rep.add(pre)

        if not pre.passed:
            rep.add(GateResult(
                "G01", "Puntuación real de Rank Math", passed=False,
                reason=f"el estimador da {est['score']}/100; no se abre el navegador. "
                       f"El post se queda en borrador"))
            return salir()

        for intentos in range(1, MAX_ITERACIONES_SCORE + 1):
            g1 = g01_real_score(site_key, post["id"], headless=headless)
            score = (g1.details or {}).get("score")
            screenshot = (g1.details or {}).get("screenshot")
            if g1.passed or not necesita_iterar(score) or intentos == MAX_ITERACIONES_SCORE:
                rep.add(g1)
                break
            print(f"  {score}/100 — se itera el contenido (intento {intentos}/{MAX_ITERACIONES_SCORE})")
            from tools.seo_estimator import estimate, sugerencias
            from tools.writer import improve_blog
            mejor = improve_blog(site_key, blog_data, sugerencias(estimate(blog_data, site_url)),
                                 score_actual=score)
            if not mejor:
                rep.add(g1)
                break
            mejor["content"], _ = sanitize(mejor.get("content", ""), mejor.get("title", ""))
            blog_data.update(mejor)
            update_draft(site_key, post["id"], blog_data)

        if not rep.ok:
            return salir()

        # ── Publicación ──────────────────────────────────────────────────────
        print("\n[wp] Todas las compuertas pasaron: se publica")
        publicado = promote_to_publish(site_key, post["id"])
        if not publicado:
            rep.add(GateResult("WP", "Promoción a publicado", passed=False,
                               reason="WordPress rechazó el cambio de estado"))
            return salir()
        post = publicado

        if image_bytes and img:
            image_registry.register(site_key, image_bytes,
                                    filename=media_info.get("filename", ""),
                                    width=img.get("width"), height=img.get("height"),
                                    unsplash_id=img.get("unsplash_id", ""),
                                    post_id=post["id"], media_id=media_id,
                                    url=media_info.get("source_url", ""))
        topic_index.record(site_key, post, blog_data["content"],
                           blog_data.get("rank_math_focus_keyword", ""))

        if SITES[site_key].get("faq_schema_via_meta"):
            from tools.wordpress import set_faq_schema_meta
            set_faq_schema_meta(site_key, post["id"], blog_data["content"])

        # ── Verificación posterior ───────────────────────────────────────────
        print("\n[post] Verificación posterior a la publicación")
        postcheck = site_health.verify_published(site_key, post, blog_data["content"], media_id)
        for k, v in postcheck.items():
            if isinstance(v, dict):
                print(f"  {'OK ' if v.get('ok') else 'NO '} {k}")
        fallos = [k for k, v in postcheck.items() if isinstance(v, dict) and not v.get("ok")]
        if fallos:
            print(f"  AVISO: comprobaciones posteriores con fallo: {fallos}")

        from tools.logger import log_post
        log_post(site_key, topic, post, success=True)
        return salir(publicado=True)

    except Exception as e:
        traceback.print_exc()
        rep.add(GateResult("ERR", "Excepción del pipeline", passed=False, reason=str(e)))
        if post and post.get("status") == "draft":
            print(f"[pipeline] El borrador #{post['id']} se queda como borrador.")
        return salir()
