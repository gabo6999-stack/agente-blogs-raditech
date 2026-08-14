# Agente de Blogs — multi-sitio

Publica artículos en WordPress vía REST para `raditech`, `tnrvisual`, `cmlc` y `propertyledger`.

**Su misión no es publicar: es publicar sólo lo que está listo para rankear.** Si un artículo no pasa
las validaciones, se queda en borrador y se reporta por qué. Nunca se publica a medias.

---

## Flujo

`publisher.py::run_guarded_pipeline` — el post se crea como **borrador**, pasa diez compuertas y sólo
entonces se promueve a publicado.

```
 0  salud del sitio        5 URLs, sin caché, UA Googlebot        -> si falla, no se publica
10  ritmo                  máx 2/día, mín 4h, parada por ráfaga
 3  duplicado por tema     ANTES de escribir nada
    ── generación (Claude + web_search) + saneado determinista ──
 5  un solo H1    7  HTML válido    8  metadata Rank Math    4  slug    3  duplicado (con H2 reales)
 9  enlaces verificados    301 -> destino final, 404 -> enlace fuera
 2  imagen                 SHA-256 contra el registro; si repite, se pide otra
    ── se crea el BORRADOR ──
 4  slug REAL de WordPress  sufijo -N  -> a la papelera y se aborta
 6  categoría realmente asignada
 2  alt + miniaturas thumbnail/medium responden 200
 1  Rank Math en el editor real (hasta 3 iteraciones si sale 70-80)
    ── sólo entonces se publica ──
    verificación posterior (200, H1, canonical, robots, sitemap) + reporte
```

## Compuertas

| # | Qué exige | Módulo |
|---|---|---|
| 1 | Puntuación de Rank Math ≥ 81, leída del editor. Nunca estimada | `gates/rankmath.py` |
| 2 | Imagen destacada, alt con la keyword, no repetida, miniaturas vivas | `gates/media.py` |
| 3 | Ningún tema duplicado (título, H1, focus keyword, solape de H2 ≥ 60%) | `gates/seo.py` |
| 4 | Slug ≤ 6 palabras, sin sufijo `-N` | `gates/seo.py` |
| 5 | Cero `<h1>` en el cuerpo, jerarquía sin saltos | `gates/content.py` |
| 6 | Categoría real del sitio, nunca Uncategorized, no se crean nuevas | `gates/taxonomy.py` |
| 7 | HTML válido: `<li>` en lista, etiquetas balanceadas, sin style/script | `gates/content.py` |
| 8 | `rank_math_title` ≤ 60, `description` 150-160, focus keyword única | `gates/seo.py` |
| 9 | ≥ 3 internos vivos + ≥ 2 externos, ≥ 1 a página de servicio | `gates/links.py` |
| 10 | Máx 2/día, mín 4h; > 3 en 1h = parada de emergencia | `gates/cadence.py` |

## Variables de entorno

```
SITE4_WP_URL / SITE4_WP_USER / SITE4_WP_PASSWORD    contraseña de aplicación (REST API)
SITE4_WP_LOGIN_PASSWORD                             contraseña REAL de la cuenta — compuerta 1
DATA_DIR=/data                                      volumen persistente — OBLIGATORIO
ANTHROPIC_API_KEY / UNSPLASH_ACCESS_KEY
RANKMATH_MIN_SCORE=81                               umbral de la compuerta 1
RANKMATH_PREFILTER_MIN=70                           umbral del pre-filtro barato
```

**`DATA_DIR` no es opcional.** Sin un volumen montado, el índice de temas y el registro de imágenes
se borran en cada redeploy y el agente vuelve a escribir artículos que ya publicó. El agente avisa
al arrancar si detecta que no está configurado.

**`SITE*_WP_LOGIN_PASSWORD`**: `wp-login.php` no acepta contraseñas de aplicación, y el editor de
bloques sólo carga con sesión de wp-admin. Sin esta variable la compuerta 1 falla siempre y no se
publica nada. Es a propósito: sin lectura real no hay puntuación que valga.

## Instalación

```bash
pip install -r requirements.txt
python -m playwright install chromium    # compuerta 1
```

## Endpoints

```
POST /publish {site_key, topic?, dry_run?}   publica (o sólo evalúa, con dry_run)
GET  /gates/{site}                           salud, ritmo, parada, estado del índice
POST /halt/{site}/clear                      quita la parada de emergencia (manual a propósito)
POST /index/{site}/refresh                   reconstruye el índice de temas desde WordPress
GET  /report/last  ·  GET /reports           reportes por artículo
POST /edit {site_key, post_id, instruction}  edición con IA de un post existente
```

## Reportes

Por cada corrida se guarda en `$DATA_DIR/reports/` un JSON y un Markdown con: qué compuertas pasó,
la puntuación real de Rank Math, la captura del panel, y cada URL verificada con su código HTTP.

## Auditoría

`audit/` contiene los scripts que produjeron el
[informe del 14-ago-2026](audit/INFORME-propertyledger-2026-08-14.md). Ninguno escribe en WordPress.

## Gotchas conocidos

- **`rank_math_*` no persiste** por el campo `meta` de `/wp/v2/posts`: devuelve 200 y lo ignora.
  Hay que usar `POST /wp-json/rankmath/v1/updateMeta` (`tools/wordpress.py::set_rankmath_meta`).
- **Los nombres de categoría vienen HTML-codificados** de WordPress (`HOA &amp; Condo Accounting`).
  Buscar con `?search=` y el `&` literal no encuentra nada. Ver `resolve_category`.
- **propertyledger.us devuelve 403 a User-Agents de navegador** en varias rutas y 200 a Googlebot.
  Toda verificación de URLs usa el UA de Googlebot (`tools/http.py`).
- **La puntuación de Rank Math no existe del lado del servidor**: se calcula en JS en el editor.
- **`last_used` de las contraseñas de aplicación sólo se actualiza una vez cada 24 h**, así que no
  sirve para descartar el uso de una llave dentro de esa ventana.
