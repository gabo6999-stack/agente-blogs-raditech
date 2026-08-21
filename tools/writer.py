import json
import anthropic
from json_repair import repair_json
from config import ANTHROPIC_API_KEY, SITES
from prompts.system import get_system_prompt
from tools.faq_schema import rebuild_faq_jsonld


def _parse_json(text: str) -> dict:
    """Extrae y parsea JSON de la respuesta de Claude, con reparación automática."""
    clean = text.strip()
    if "```" in clean:
        parts = clean.split("```")
        for part in parts[1::2]:
            candidate = part.lstrip("json").strip()
            if candidate.startswith("{"):
                clean = candidate
                break
    clean = clean.strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        repaired = repair_json(clean, return_objects=True)
        if isinstance(repaired, dict):
            return repaired
        raise ValueError(f"No se pudo parsear el JSON: {clean[:200]}")


def edit_blog(site_key: str, current_post: dict, instruction: str) -> dict:
    """
    Usa Claude para corregir/editar un blog existente según una instrucción.
    Retorna el mismo diccionario de blog_data con los cambios aplicados.
    """
    site = SITES[site_key]
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    language = site.get("language", "es")

    if language == "en":
        system_prompt = f"""You are an expert SEO content editor specialized in {site['niche']}.
Your task is to correct and improve an existing blog article according to the editor's instructions.

INSTRUCTIONS:
- Language: US English
- Tone: professional but accessible, precise but easy to understand
- Apply ONLY the changes requested by the editor
- Keep the existing HTML structure unless told otherwise
- Preserve all correct information from the original article
- NEVER include <img> tags in the content — images are handled separately

RESPONSE FORMAT:
Respond ONLY with valid JSON in this EXACT field order. The large "content" field MUST come LAST so metadata is never lost if the response is long:
{{
  "title": "Article title",
  "slug": "article-title-in-slug-form",
  "rank_math_title": "SEO meta title (60 characters max)",
  "rank_math_description": "SEO meta description (160 characters max)",
  "rank_math_focus_keyword": "primary keyword",
  "tags": ["tag1", "tag2", "tag3"],
  "unsplash_query": "2-3 word English query to search a related image on Unsplash",
  "excerpt": "Summary, 150 characters max",
  "content": "Full HTML content of the article (this field LAST)"
}}

JSON RULES:
- Emit all small metadata fields FIRST, then "content" LAST.
- The "content" field is HTML — escape ALL internal quotes as \\\"
- Do not include the H1 inside content, only the article body
- Do not add text outside the JSON"""
    else:
        system_prompt = f"""Eres un experto editor de contenido SEO especializado en {site['niche']}.
Tu tarea es corregir y mejorar un artículo de blog existente según las instrucciones del editor.

INSTRUCCIONES:
- Idioma: español (México)
- Tono: profesional pero accesible, científico pero entendible
- Aplica SOLO los cambios indicados por el editor
- Mantén la estructura HTML existente a menos que se indique lo contrario
- Conserva toda la información correcta del artículo original
- NUNCA incluyas etiquetas <img> en el content — las imágenes se manejan por separado

FORMATO DE RESPUESTA:
Responde ÚNICAMENTE con un JSON válido en ESTE orden exacto de campos. El campo grande "content" DEBE ir AL FINAL para que el metadata nunca se pierda si la respuesta es larga:
{{
  "title": "Título del artículo",
  "slug": "titulo-del-articulo-en-slug",
  "rank_math_title": "Meta title SEO (60 caracteres máximo)",
  "rank_math_description": "Meta description SEO (160 caracteres máximo)",
  "rank_math_focus_keyword": "keyword principal",
  "tags": ["tag1", "tag2", "tag3"],
  "unsplash_query": "2-3 palabras en inglés para buscar imagen en Unsplash",
  "excerpt": "Resumen de 150 caracteres máximo",
  "content": "Contenido HTML completo del artículo (este campo AL FINAL)"
}}

REGLAS DEL JSON:
- Emite primero todos los campos de metadata y el "content" AL FINAL.
- El campo "content" es HTML — escapa TODAS las comillas internas como \\\"
- No incluyas el H1 dentro del content, solo el cuerpo del artículo
- No agregues texto fuera del JSON"""

    tags_str = ", ".join(current_post.get("tags", [])) or "(ninguno)"
    user_message = f"""Corrige y mejora el siguiente artículo según esta instrucción:

INSTRUCCIÓN DEL EDITOR: {instruction}

ARTÍCULO ACTUAL:
Título: {current_post.get('title', '')}
Excerpt: {current_post.get('excerpt', '')}
Meta title: {current_post.get('rank_math_title', '')}
Meta description: {current_post.get('rank_math_description', '')}
Focus keyword: {current_post.get('rank_math_focus_keyword', '')}
Tags: {tags_str}

CONTENIDO ACTUAL:
{current_post.get('content', '')}

Responde únicamente con el JSON corregido."""

    print(f"[Writer] Editando post con instrucción: {instruction}")

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=20000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )

    # Ver el comentario largo en generate_blog(): si la respuesta se corto por
    # limite de tokens, el JSON "content" queda a medias y repair_json lo
    # cierra en silencio sin que nadie se entere. Abortar antes de parsear.
    if response.stop_reason == "max_tokens":
        raise RuntimeError(
            "[Writer] La respuesta de Claude se cortó por límite de tokens "
            "(max_tokens=20000) editando el post. NO se publica contenido truncado."
        )

    full_text = "".join(block.text for block in response.content if hasattr(block, "text"))

    try:
        blog_data = _parse_json(full_text)
        if blog_data.get("content"):
            blog_data["content"] = rebuild_faq_jsonld(
                blog_data["content"], include_script=not site.get("faq_schema_via_meta"))
        print(f"[Writer] Blog editado: {blog_data.get('title', 'Sin título')}")
        return blog_data
    except Exception as e:
        print(f"[Writer] Error parseando JSON: {e}")
        print(f"[Writer] Respuesta cruda: {full_text[:500]}")
        raise


def improve_blog(site_key: str, blog_data: dict, fallos: str, score_actual: int = None) -> dict | None:
    """Itera un artículo que se quedó corto de puntuación (compuerta 1).

    Solo se llama cuando Rank Math devolvió entre 70 y 80: ahí el problema es de
    retoque y vale la pena reintentar (máximo 3 veces). Por debajo de 70 el
    problema es de fondo y el post se queda en borrador.
    """
    site = SITES[site_key]
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    language = site.get("language", "es")

    if language == "en":
        system_prompt = f"""You are an SEO editor for {site['niche']}.
Improve the article so it scores higher in Rank Math, WITHOUT padding it and WITHOUT
changing the topic. Fix exactly the failing checks listed by the editor.

HARD RULES:
- Do NOT put an <h1> in the content. The template renders the H1 from the post title.
- Every <li> must sit inside a <ul> or <ol>.
- Keep at least 3 internal links and 2 external links already present — do not invent new URLs.
- Do not add inline style attributes and do not write any <script>/JSON-LD.
- Keep the FAQ section (<h2>Frequently Asked Questions</h2> + 4 <h3>/<p> pairs).

RESPONSE FORMAT — valid JSON, metadata first and "content" LAST:
{{
  "title": "...", "slug": "...", "rank_math_title": "max 60 chars",
  "rank_math_description": "150-160 chars", "rank_math_focus_keyword": "one keyword",
  "tags": ["..."], "category": "...", "excerpt": "...", "content": "full HTML (LAST)"
}}
No text outside the JSON."""
    else:
        system_prompt = f"""Eres un editor SEO especializado en {site['niche']}.
Mejora el artículo para que puntúe más alto en Rank Math, SIN rellenar y SIN cambiar
el tema. Corrige exactamente los checks que el editor marca como fallidos.

REGLAS DURAS:
- NO pongas ningún <h1> en el content. La plantilla genera el H1 desde el título.
- Todo <li> debe ir dentro de un <ul> o <ol>.
- Conserva los 3 enlaces internos y 2 externos que ya trae — no inventes URLs nuevas.
- Sin atributos style en línea y sin escribir ningún <script>/JSON-LD.
- Conserva la FAQ (<h2>Preguntas frecuentes</h2> + 4 pares <h3>/<p>).

FORMATO DE RESPUESTA — JSON válido, metadata primero y "content" AL FINAL:
{{
  "title": "...", "slug": "...", "rank_math_title": "máx 60 caracteres",
  "rank_math_description": "150-160 caracteres", "rank_math_focus_keyword": "una keyword",
  "tags": ["..."], "category": "...", "excerpt": "...", "content": "HTML completo (AL FINAL)"
}}
No agregues texto fuera del JSON."""

    user_message = f"""Rank Math le dio {score_actual}/100 a este artículo y necesita al menos 81.

CHECKS QUE ESTÁN FALLANDO (los de más peso primero):
{fallos}

ARTÍCULO ACTUAL:
Título: {blog_data.get('title', '')}
Meta title: {blog_data.get('rank_math_title', '')}
Meta description: {blog_data.get('rank_math_description', '')}
Focus keyword: {blog_data.get('rank_math_focus_keyword', '')}
Slug: {blog_data.get('slug', '')}

CONTENIDO:
{blog_data.get('content', '')}

Responde solo con el JSON corregido."""

    print(f"[Writer] Iterando el artículo (Rank Math dio {score_actual})")
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=20000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        # Ver el comentario largo en generate_blog(): respuesta cortada por
        # limite de tokens = "content" a medias que repair_json cierra en
        # silencio. Tratarlo como fallo de la iteracion (ya cae en el except
        # de abajo, que devuelve None y el caller conserva la version buena).
        if response.stop_reason == "max_tokens":
            raise RuntimeError("la respuesta se cortó por límite de tokens (max_tokens=20000)")
        full_text = "".join(b.text for b in response.content if hasattr(b, "text"))
        mejor = _parse_json(full_text)
        if mejor.get("content"):
            mejor["content"] = rebuild_faq_jsonld(
                mejor["content"], include_script=not site.get("faq_schema_via_meta"))
        return mejor
    except Exception as e:
        print(f"[Writer] No se pudo iterar el artículo: {e}")
        return None


def generate_blog(site_key: str, topic: str) -> dict:
    """
    Usa Claude con web_search para investigar y escribir el blog completo.
    Retorna diccionario con título, contenido, SEO metadata, etc.
    """
    site = SITES[site_key]
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    language = site.get("language", "es")

    system_prompt = get_system_prompt(site["niche"], site["post_length"], site.get("prompt_profile"), language)

    if language == "en":
        user_message = f"""Write a complete, SEO-optimized blog article about: "{topic}"

Research with web_search to include current information, recent studies and accurate data.
The article should be useful for people interested in {site['niche']}.
Respond only with the requested JSON."""
    else:
        user_message = f"""Escribe un artículo de blog completo y optimizado para SEO sobre: "{topic}"

Investiga con web_search para incluir información actualizada, estudios recientes y datos precisos.
El artículo debe ser útil para personas interesadas en {site['niche']}.
Responde únicamente con el JSON solicitado."""

    print(f"[Writer] Generando blog sobre: {topic}")

    messages = [{"role": "user", "content": user_message}]

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=20000,
        system=system_prompt,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=messages
    )

    while response.stop_reason == "tool_use":
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "Search completed"
                })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=20000,
            system=system_prompt,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages
        )

    # La respuesta se corto (limite de tokens u otra causa): "content" va AL
    # FINAL del JSON justamente para que esto se pueda detectar, pero nadie
    # lo revisaba. json.loads fallaba (string sin cerrar), y el fallback
    # repair_json "arreglaba" el JSON cerrando el string a medio texto SIN
    # saberlo — deja el HTML cortado a mitad de una oracion, sin cerrar
    # </li></ul>, sin FAQ, sin conclusion, y el post se publicaba igual. Asi
    # salio el post #31 de cmlc el 2026-07-14 (rayos X a domicilio, cortado
    # en medio de un <li>). Con esto se aborta ANTES de intentar parsear.
    if response.stop_reason == "max_tokens":
        raise RuntimeError(
            f"[Writer] La respuesta de Claude se cortó por límite de tokens "
            f"(max_tokens=20000) generando '{topic}'. NO se publica contenido truncado."
        )

    full_text = "".join(block.text for block in response.content if hasattr(block, "text"))

    try:
        blog_data = _parse_json(full_text)
        if blog_data.get("content"):
            blog_data["content"] = rebuild_faq_jsonld(
                blog_data["content"], include_script=not site.get("faq_schema_via_meta"))
        print(f"[Writer] Blog generado: {blog_data.get('title', 'Sin título')}")
        return blog_data
    except Exception as e:
        print(f"[Writer] Error parseando JSON: {e}")
        print(f"[Writer] Respuesta cruda: {full_text[:500]}")
        raise
