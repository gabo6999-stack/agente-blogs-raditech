# Auditoría y rediseño del agente "Blogs Raditech" — sitio propertyledger.us

**Fecha:** 14 de agosto de 2026
**Alcance:** código y configuración del agente, estado real del sitio, e implementación de las diez compuertas de bloqueo.
**Método:** todo lo que sigue sale de peticiones a la REST API y al sitio en vivo. Los scripts que las hicieron están en `audit/` y se pueden volver a correr.

---

## Resumen

Se auditaron los **34 posts** que existen hoy en propertyledger.us (32 publicados + 2 borradores). Cuatro de los siete problemas del informe original se confirman tal cual, dos se confirman con matices y **uno resultó ser falso**. Además aparecieron tres hallazgos nuevos que no estaban en el informe y que explican mejor lo que pasó.

El cambio de fondo ya está implementado: el agente **ya no publica directamente**. Crea el post como borrador, lo somete a diez compuertas y sólo lo publica si todas pasan.

---

## 1. Cómo funciona el agente (estado que se encontró)

| | |
|---|---|
| **Repo** | `C:\Users\gabom\Proyectos\agente-blogs-raditech` → `github.com/gabo6999-stack/agente-blogs-raditech` |
| **Despliegue** | Railway, `Procfile`: `web: python pipeline.py` |
| **Disparo** | Hilo con la librería `schedule`. propertyledger: lunes a viernes 09:00. También `POST /publish` manual desde el dashboard |
| **Tema** | `tools/trends.py` → cola curada `content_cache/propertyledger.json` (25 temas de DataForSEO); al agotarse, Google Trends; al fallar, `keywords_seed` |
| **Redacción** | `tools/writer.py` → Claude Sonnet 4.5 con `web_search`, devuelve un JSON con `title/slug/rank_math_*/tags/category/excerpt/content` |
| **Imagen** | `tools/images.py` → Unsplash, primer resultado, se sube a la biblioteca |
| **Publicación** | `tools/wordpress.py::publish_post` → `POST /wp/v2/posts` con **`status: "publish"` directo** |
| **Validaciones** | **Ninguna.** No había ni una sola comprobación entre generar y publicar |

Ese último punto es la causa raíz de todo lo demás: entre "Claude devolvió un JSON" y "está publicado en Google" no había nada.

---

## 2. Qué cambió el 11 de agosto

**Respuesta corta: en el agente, nada.**

```
$ git log --format='%h | %ad | %s' --date=iso -3
b5c3904 | 2026-07-26 08:11:32 -0600 | feat(web): buscador de blog para CMLC
9b35095 | 2026-07-26 07:42:33 -0600 | feat(web): buscador de blog para Property Ledger Solutions
40ae0b1 | 2026-07-25 06:29:18 -0600 | feat(cmlc): FAQ schema via Rank Math meta para posts nuevos
$ git status --short
(vacío)
```

El último commit es del **26 de julio**. No hay cambios de código, ni prompt, ni configuración el 11 de agosto ni después.

### La premisa del informe original era incorrecta en un punto

> "Los 10 artículos publicados desde el 11 de agosto no tienen `rank_math_seo_score`, `rank_math_title` ni `rank_math_description`"

Lo de `rank_math_seo_score` **es cierto**. Lo de `rank_math_title` y `rank_math_description` **no**. Lectura literal del post #322, publicado el 13 de agosto:

```
  post #322 (gavitoa, 2026-08-13)
    rank_math_title             = 'HOA &amp; Condo Financial Statements: Monthly Board Review Guide'
    rank_math_description       = 'Learn which financial statements HOA and condo boards must review monthly, red flags to watch for, and best practices for financial oversight and compliance.'
    rank_math_focus_keyword     = 'HOA condo financial statements'
    rank_math_seo_score         = ''
```

De los 34 posts: **0 sin `rank_math_title`, 0 sin `rank_math_description`, 0 sin `rank_math_focus_keyword`**. Sólo faltan 10 `rank_math_seo_score`. El agente sí escribe la metadata, y la escribe bien (por el endpoint `rankmath/v1/updateMeta`, que es el único que persiste).

### Por qué falta el score, y por qué no "cambió" nada

La puntuación de Rank Math se calcula en JavaScript dentro del editor de bloques. El meta `rank_math_seo_score` sólo se escribe cuando alguien abre el post en el editor. **El agente nunca lo escribió — ni antes ni después del 11 de agosto.**

Los posts anteriores tienen puntuación porque alguien los abrió en el editor. La prueba está en los tiempos de modificación:

```
  id    score  date_gmt             modified_gmt         editado_despues
  318   -      2026-08-12T09:03:49  2026-08-12T09:03:52  True   <- 3 segundos: sólo el propio agente
  322   -      2026-08-13T09:03:57  2026-08-13T09:04:01  True   <- 4 segundos: sólo el propio agente
  84    80     2026-07-16T16:05:27  2026-08-11T00:21:14  True   <- 26 días después: un humano en el editor
  109   69     2026-07-20T14:02:01  2026-08-11T00:08:00  True
  158   76     2026-07-23T09:08:31  2026-08-11T00:23:55  True
```

#318 y #322 se modificaron 3 y 4 segundos después de publicarse: ese es el PATCH del propio agente, nadie los tocó, y salieron sin score. Los que sí tienen score fueron editados días o semanas después — en las sesiones manuales del 10 al 14 de agosto.

**Lo que realmente pasó el 11 de agosto no es que el agente cambiara: es que se dejó de revisar a mano lo que publicaba.**

---

## 3. Lo que sí apareció el 12 de agosto: un segundo publicador

Los 7 posts de las 00:11–01:10 UTC del 12 de agosto **no los produjo este agente**. No es una hipótesis: no coinciden con su salida en cinco dimensiones independientes, todas comprobables.

| | Agente (p.ej. #216, #318, #322) | Ráfaga del 12-ago (#309–#316) |
|---|---|---|
| Longitud del cuerpo | 1.800–3.800 palabras | **556–888 palabras** |
| `<h1>` en el cuerpo | 0 (el prompt lo prohíbe explícitamente) | **1, idéntico al título** |
| Enlaces internos / externos | 6 / 2 | **0 / 0** |
| Categoría | real | **Uncategorized** |
| Encabezado del cuerpo | el texto del artículo | **comentario de briefing** |

El arranque literal del `content.raw` del post #309:

```html
<!--
  SEO Title: What Is Trust Accounting in Property Management? A Plain-English Guide
  Meta Description: Learn what trust accounting means for property management, why it matters, and how to stay compliant. Plain-English guide with examples.
  Slug: /what-is-trust-accounting-property-management/
  Focus Keyword: what is trust accounting
  Images:
    - trust-accounting-explainer.jpg | ALT: What is trust accountin...
```

Y tras el comentario, el cuerpo viene envuelto en `<div class="pls-root pls-blog alignfull">` con su propio bloque `<style>` y un `@import` de Google Fonts. El agente nunca genera nada de eso: su prompt pide HTML semántico (`h2/h3/p/ul/strong/table`) y le prohíbe escribir `<script>`.

El prompt del agente, en las tres variantes, dice literalmente: *"No incluyas el H1 dentro del content, solo el cuerpo del artículo"*. Los 25 posts que sí son suyos lo cumplen. Los 7 de la ráfaga, no.

### Contraseñas de aplicación (lectura en vivo)

```
--- usuario 3 (gavitoa) ---
    nombre='Agente Blogs Raditech'
      uuid=9cbb67d3-1a24-43b3-aba5-b5f842e74832  creada=2026-07-20T13:38:06
      ultimo_uso=2026-08-13T09:03:18  ultima_ip=152.55.176.163
    nombre='Claude SEO'
      uuid=3bdc73eb-dd92-4fff-af2b-80799b2bac24  creada=2026-07-31T13:18:54
      ultimo_uso=2026-08-11T23:26:09  ultima_ip=2806:262:48a:895b:1c79:2631:66a1:cc8a

--- usuario 1 (plsadmin) ---
    nombre='claude'
      uuid=6c85f77b-c123-48e4-b234-93952cb9159d  creada=2026-07-14T14:00:42
      ultimo_uso=2026-08-13T14:01:15  ultima_ip=177.53.212.234
```

El `ultimo_uso` de "Agente Blogs Raditech" (2026-08-13T09:03:18) encaja con el post #322 (publicado 09:03:57). Las IPs separan claramente los dos orígenes: el agente sale de una IPv4 fija; "Claude SEO" salió de una IPv6 residencial mexicana.

**Aviso importante para no sacar conclusiones de más:** WordPress sólo actualiza `last_used` **una vez cada 24 horas** (`WP_Application_Passwords::record_application_password_usage()` sale antes de tiempo si `last_used + DAY_IN_SECONDS > time()`). Así que "último uso: 11-ago 23:26" **no** significa que no se usara después: cubre sin registrar toda la ventana hasta el 12-ago 23:26, dentro de la cual cae la ráfaga. Ese campo no sirve ni para acusar ni para descartar. Lo que sí queda establecido por el contenido es que **la ráfaga no salió de este código**.

---

## 4. Verificación punto por punto del informe original

| Problema reportado | Veredicto | Evidencia |
|---|---|---|
| Contenido duplicado (9 temas en 2-3 URLs) | **CONFIRMADO** | 5 grupos de duplicados; 17 posts implicados. #219/#221/#313 son el mismo artículo ("Setting Up a Property Management Chart of Accounts the Right Way") en 3 URLs |
| Publicación en ráfaga | **CONFIRMADO, con corrección** | 8 posts el 12-ago, pero **7** entre 00:11 y 01:10 (no 8). El octavo salió a las 09:03. Faltan los IDs #312 (en la papelera) y #317 (borrado), así que la ráfaga original fue mayor |
| Sin metadata SEO | **PARCIALMENTE FALSO** | Faltan 10 `rank_math_seo_score`. `rank_math_title`/`description`/`focus_keyword` están **en los 34 posts** |
| Sin categoría (13 de 25) | **CONFIRMADO, cifra distinta** | **16 de 34** posts llevan "Uncategorized"; **10** la llevan como única categoría |
| H1 duplicado | **CONFIRMADO** | 7 posts, todos de la ráfaga del 12-ago, con `<h1>` idéntico al título |
| HTML inválido (`<li>` sueltos) | **NO REPRODUCIDO** | **0 de 34** posts tienen `<li>` fuera de `<ul>`/`<ol>` en `content.raw`. Es posible que se observara sobre el HTML renderizado. La compuerta 7 lo comprueba igualmente, y se probó con casos sintéticos |
| Colisión de slugs | **CONFIRMADO** | 1 caso: `security-deposit-accounting-property-managers-compliance-best-practices-2` (post #212) |
| Enlaces internos a URLs muertas | **CONFIRMADO y peor de lo pensado** | Ver hallazgo nuevo nº2 |

---

## 5. Hallazgos nuevos

### 5.1. El bug de la categoría: WordPress guarda el nombre con la entidad HTML codificada

Prueba literal:

```
  categorias existentes: {"22": "HOA &amp; Condo Accounting", "11": "Property Management Accounting", "26": "Trust Accounting", "1": "Uncategorized"}

  search='HOA & Condo Accounting'         -> []
  search='HOA &amp; Condo Accounting'     -> [(22, 'HOA &amp; Condo Accounting', 'hoa-condo-accounting')]
  search='Condo Accounting'               -> [(22, 'HOA &amp; Condo Accounting', 'hoa-condo-accounting')]
  search='Financial Reporting'            -> []
```

`get_or_create_category()` buscaba con `?search=` usando el `&` literal → no encontraba nada → intentaba **crear** una categoría que ya existía → WordPress responde `term_exists` (no 201) → la función devolvía `None` → el payload salía sin `categories` → WordPress asignaba **Uncategorized**. Es exactamente lo que le pasó al post #322 del 13 de agosto.

Además, `config.py` ofrecía al redactor una categoría **"Financial Reporting" que no existe en el sitio**.

**Corregido:** `resolve_category()` lista todas las categorías y compara decodificando las entidades; y ya no crea ninguna (la compuerta 6 lo prohíbe sin aprobación). "Financial Reporting" se quitó de `config.py`.

### 5.2. El propio `config.py` inyectaba enlaces rotos en cada artículo

Verificación con 3 intentos por URL, sin seguir redirecciones, resultado estable 3/3:

```
path                                                    Chrome x3             Googlebot x3
/                                                       200,200,200           200,200,200
/contact/                                               403,403,403           200,200,200
/monthly-accounting/                                    200,200,200           200,200,200
/property-management-accounting/                        403,403,403           200,200,200
/hoa-condo-accounting/                                  404,404,404           404,404,404
/property-management-trust-accounting/                  403,403,403           200,200,200
/property-management-financial-statements/              403,403,403           200,200,200
/hoa-accounting-basics-guide-board-members-treasurers/  403,403,403           404,404,404
/what-is-trust-accounting-property-management-guide/    200,200,200           200,200,200
/property-management-bookkeeping-vs-accounting/         403,403,403           301>,301>,301>
/setting-up-property-management-chart-of-accounts/      403,403,403           301>,301>,301>
```

Dos entradas de `internal_links` estaban muertas:

- **`/hoa-condo-accounting/` → 404 para todos.** El post #322 la enlazó **dos veces**.
- **`/hoa-accounting-basics-guide-board-members-treasurers/` → 404 para Googlebot.** Es el post **#115, que sigue en BORRADOR** desde el 20 de julio.

**Corregido:** ambas fuera de `config.py`, con la nota de cuándo volver a meterlas. La compuerta 9 revalida cada enlace en cada artículo de todas formas.

### 5.3. El edge devuelve 403 a navegadores y 200 a Googlebot

Mismo URL, distintos User-Agent:

```
  301     3724 ms  (sin UA / python-requests)
  403      977 ms  Mozilla/5.0 (corto)          -> openresty/1.25.3.1 detrás de Cloudflare
  403      957 ms  Chrome completo
  301     3406 ms  Googlebot clasico
  301     2304 ms  Googlebot smartphone-ish
  301      903 ms  curl/8.4.0
```

No es saturación: 12 peticiones seguidas a la home dieron `[200 × 12]` con latencia estable (~870 ms).

Consecuencia de diseño: **el verificador de enlaces usa el User-Agent de Googlebot**. Con un UA de navegador marcaría como rotos enlaces que Google ve perfectamente.

### Sobre el 5xx de Search Console

**No se reprodujo ningún 5xx.** Ni con UA de navegador ni con UA de Googlebot, en ninguna de las ~60 peticiones de esta auditoría. Lo que sí se midió es el 403 selectivo de arriba y dos 404 reales. No puedo confirmar ni descartar lo que reportó Search Console el 13 de agosto; sólo puedo decir que hoy, desde aquí, no ocurre. El chequeo de salud previo queda implementado y detectará el 5xx si vuelve.

**Latencias medidas** (`/` con UA de navegador llegó a 8.0 s en una de las tandas; con UA de Googlebot, 799–3.646 ms). La mediana está por debajo del umbral de 3 s, pero la home es el punto más lento del sitio.

---

## 6. Qué habrían evitado las compuertas

Se pasaron los 34 posts reales por las compuertas nuevas (`audit/replay_gates.py`, no escribe nada en WordPress):

```
  posts que las compuertas HABRIAN BLOQUEADO : 34/34
  posts que habrian pasado limpios           :  0/34

  disparos por compuerta:
    G01   34 posts  — puntuacion Rank Math < 81 o ausente
    G08   23 posts  — metadata de Rank Math incompleta
    G03   17 posts  — duplicado de tema
    G06   16 posts  — Uncategorized o categoria inexistente
    G04   14 posts  — slug sucio o con sufijo -N
    G05    7 posts  — H1 en el cuerpo / jerarquia

  ritmo de publicacion (historico completo):
    dias por encima de 2 posts/dia : ['2026-07-16', '2026-08-12']
    gaps por debajo de 4h          : 11
    ventanas de rafaga (>3 en 1h)  : 5
```

**Un dato que conviene mirar de frente: el umbral de 81 no lo ha alcanzado nunca ningún post de este sitio.** La mejor puntuación registrada es **80** (posts #84 y #98); la mediana de los 24 que tienen score es 76. Con el umbral tal y como está especificado, el agente publicaría **cero** artículos hasta que la calidad suba. Eso es coherente con "es preferible no publicar a publicar mal", pero es una decisión de negocio que conviene tomar a sabiendas, no descubrir en producción.

---

## 7. Qué se implementó

### Las diez compuertas

| # | Compuerta | Módulo | Cuándo corre |
|---|---|---|---|
| 1 | Puntuación Rank Math ≥ 81 | `gates/rankmath.py` | sobre el borrador, en navegador real |
| 2 | Imagen destacada única, con alt y miniaturas vivas | `gates/media.py` | antes y después de crear el borrador |
| 3 | Sin duplicados de tema | `gates/seo.py` | **antes de escribir** y otra vez con los H2 reales |
| 4 | Slug limpio, sin colisiones | `gates/seo.py` | sobre el propuesto y sobre el que devuelve WordPress |
| 5 | Un solo H1 | `gates/content.py` | sobre el contenido generado |
| 6 | Categoría real, nunca Uncategorized | `gates/taxonomy.py` | sobre el borrador ya creado |
| 7 | HTML válido | `gates/content.py` | sobre el contenido generado |
| 8 | Metadata de Rank Math completa | `gates/seo.py` | sobre el contenido generado |
| 9 | Enlaces internos verificados | `gates/links.py` | sobre el contenido generado |
| 10 | Ritmo de publicación | `gates/cadence.py` | lo primero de todo |

Cada compuerta devuelve un `GateResult` con `passed`, `reason` y la evidencia cruda. Las subcompuertas se numeran (`G05a`, `G05b`…) para que el reporte diga exactamente qué falló.

### El flujo nuevo

```
 0  salud del sitio        (5 URLs, sin caché, UA Googlebot)     -> si falla, no se publica
10  ritmo                  (máx 2/día, mín 4h, parada por ráfaga)
 3  duplicado por tema     ANTES de escribir nada
    ── generación + saneado determinista ──
 5  un solo H1     7  HTML válido     8  metadata     4  slug     3  duplicado (con H2 reales)
 9  enlaces verificados (301 → destino final, 404 → enlace fuera)
 2  imagen: hash SHA-256 contra el registro; si repite, se pide otra
    ── se crea el BORRADOR ──
 4  slug REAL devuelto por WordPress -> si trae sufijo -N, a la papelera y se aborta
 6  categoría realmente asignada
 2  alt + miniaturas thumbnail/medium responden 200
 1  Rank Math en el editor real (hasta 3 iteraciones si sale 70-80)
    ── sólo entonces se publica ──
    verificación posterior (200, H1, canonical, robots, sitemap) + reporte
```

### Piezas nuevas

- **`tools/store.py`** — estado persistente. `tools/logger.py` escribía en `DATA_DIR` con default `.`, y `logs/` está en `.gitignore`: en Railway sin volumen, **el historial se borraba en cada redeploy**. Por eso el agente reescribía temas ya publicados (el `-2` del post #212). Ahora `DATA_DIR` debe apuntar a un volumen y el agente **avisa a gritos** si no lo está.
- **`tools/topic_index.py`** — índice de temas por sitio (título, H1, focus keyword, H2), reconstruible desde WordPress. Normaliza colapsando cadenas repetidas del tipo `X + X`.
- **`tools/image_registry.py`** — registro por SHA-256 + nombre de archivo + dimensiones.
- **`tools/http.py`** — todas las verificaciones sin seguir redirecciones y con UA de Googlebot.
- **`tools/site_health.py`** — chequeo previo y verificación posterior a publicar.
- **`tools/seo_estimator.py`** — Opción B como pre-filtro barato.
- **`tools/rankmath_browser.py`** — Opción A: Playwright abre el editor y lee la puntuación real, con captura del panel. **Probado en vivo, ver §7.1.**
- **`tools/report.py`** — reporte por artículo en JSON y Markdown.
- **`publisher.py`** — el orquestador con compuertas.

### 7.1. La compuerta 1, probada en vivo

Se validó contra **raditech.mx** (es el único sitio con la contraseña real de la cuenta configurada;
para propertyledger falta `SITE4_WP_LOGIN_PASSWORD`). Salida literal:

```
--- raditech post #1152 ---
  meta rank_math_seo_score en la BD : ''
  score leido del editor            : 75
  metodo                            : wp.data.select('rank-math').getAnalysisScore()

--- raditech post #1148 ---
  meta rank_math_seo_score en la BD : ''
  score leido del editor            : 68
  metodo                            : wp.data.select('rank-math').getAnalysisScore()
```

**Esto cierra el hallazgo técnico de raíz.** Los dos posts tienen el meta VACÍO en la base de datos y
sin embargo el editor calcula 75 y 68. La puntuación existe; simplemente no se persiste hasta que
alguien abre el editor. Ahora el agente la lee.

Tres cosas que sólo se descubren probándolo, y que estaban mal en la primera implementación:

1. **El selector correcto es `getAnalysisScore()`, no `getScore()`.** El store `rank-math` expone
   `getAnalysisScore / getKeywords / getSelectedKeyword / getShowScoreFrontend`. `getScore()` no existe
   y devolvía `null` en silencio.

2. **Hay dos elementos con la clase `.rank-math-toolbar-score`.** El segundo lleva además
   `.content-ai-score` y muestra la puntuación de *Content AI*, que en un post sin Content AI es
   **`0 / 100`**. Un selector ingenuo lee ese cero y lo toma por la puntuación SEO — habría bloqueado
   todos los artículos por el motivo equivocado. El fallback del DOM usa
   `.seo-score .score-text` y excluye explícitamente `.content-ai-score`.

3. **El asistente Kodee de Hostinger (`#chatbot-float-box`, 360×700, z-index 9996) tapa el panel** y
   salía en la captura en vez de la puntuación. Se oculta por CSS antes de capturar. Además el lateral
   arranca en la pestaña "Entrada/Bloque": hay que pulsar `button[aria-label='Rank Math']` para que el
   panel se vea.

La captura que queda con el reporte muestra el panel completo: keyword, "SEO Básico ✓ Todo bien" con
sus seis comprobaciones, y los contadores de "Adicional: 4 Errores" y "Legibilidad del título: 2 Errores".

**De paso:** los tres posts más recientes de raditech.mx también tienen `rank_math_seo_score` vacío, y
uno de ellos tiene el slug `ris-radiologia-sistema-informacion-radiologica-2`. El sufijo `-2` es la
misma colisión que en propertyledger: **el problema no es exclusivo de este sitio**, viene del agente
compartido y las compuertas lo cubren para los cuatro.

### Endpoints nuevos

```
GET  /gates/{site}            estado de compuertas evaluables sin escribir nada
POST /halt/{site}/clear       quita la parada de emergencia (es manual a propósito)
POST /index/{site}/refresh    reconstruye el índice de temas desde WordPress
GET  /report/last             último reporte
GET  /reports                 reportes guardados
POST /publish {dry_run:true}  corre las compuertas y se detiene antes de crear el borrador
```

---

## 8. Pendientes que necesitan una decisión

1. **`SITE4_WP_LOGIN_PASSWORD` — es lo único que falta para cerrar la compuerta 1 en propertyledger.**
   El mecanismo ya está probado (§7.1), pero `wp-login.php` **no acepta contraseñas de aplicación** y
   la credencial configurada para propertyledger es de aplicación (formato de 6 grupos de 4).
   Basta añadir al `.env` (y a Railway) una línea con la contraseña real de la cuenta `GavitoA` en
   propertyledger.us:

   ```
   SITE4_WP_LOGIN_PASSWORD=<contraseña real de GavitoA en propertyledger.us>
   ```

   Sin ella la compuerta 1 falla siempre y el agente no publica. El código lo detecta y lo dice con
   ese mensaje exacto en vez de dejarlo pasar.

2. **`DATA_DIR` en Railway.** Montar un volumen y exportar `DATA_DIR=/data`. Sin esto el índice de temas y el registro de imágenes se pierden en cada redeploy, que es la raíz de los duplicados.

3. **El umbral de 81 — decidido: se mantiene estricto.** Ningún post del sitio lo ha alcanzado nunca
   (máximo histórico: 80; mediana 76). Consecuencia asumida: el agente dejará los artículos en borrador
   hasta que la calidad suba, y hay que revisarlos a mano. Se cambia con `RANKMATH_MIN_SCORE` sin tocar
   código si más adelante se quiere arrancar más abajo.

4. **`playwright install chromium`** en el contenedor de Railway (~115 MB de descarga) o mover la compuerta 1 a un worker aparte.

5. **Higiene de accesos — decidido: no se toca por ahora.** Queda anotado:
   - conservar `Agente Blogs Raditech` (gavitoa) — es el que usa este código
   - `Claude SEO` (gavitoa), uuid `3bdc73eb-dd92-4fff-af2b-80799b2bac24` — sigue activa; revocarla cuando se quiera
   - conservar `claude` (plsadmin) — activo el 13-ago desde otra IP

6. **Limpieza pendiente en el sitio** (no la toca el agente):
   - `/hoa-condo-accounting/` da 404 y es una **página de servicio**: o se republica o se quita de los menús
   - el post **#115** lleva en borrador desde el 20 de julio y está enlazado desde artículos vivos
   - `/property-management-bookkeeping-vs-accounting/` y `/setting-up-property-management-chart-of-accounts/` ya redirigen 301 bien; el resto de duplicados de la ráfaga conviene revisarlos igual

---

## 9. Cómo reproducir

```bash
python audit/collect_evidence.py propertyledger   # baja los posts con context=edit
python audit/analyze_evidence.py propertyledger   # cruza autor x defecto, duplicados, ráfagas
python audit/deep_checks.py propertyledger        # metadata, categorías, cuerpos, salud
python audit/deep_checks2.py propertyledger       # WAF/UA, capacidades, enlaces de config
python audit/deep_checks3.py                      # redirecciones, bug de categoría, estabilidad
python audit/deep_checks4.py                      # qué URLs están rotas de verdad
python audit/replay_gates.py propertyledger       # pasa los 34 posts por las compuertas
python audit/test_gates.py                        # compuertas contra el contenido defectuoso real
```

Ninguno escribe en WordPress.
