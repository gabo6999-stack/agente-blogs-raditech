# Consolidación de duplicados en propertyledger.us — estado y plan

**Fecha:** 14 de agosto de 2026
**Método:** `audit/plan_consolidacion.py`, peticiones sin seguir redirecciones y con User-Agent de Googlebot.

---

## Conclusión: los 301 ya están hechos

Esperaba tener que crearlos. **No hace falta ninguno.** Los 6 duplicados redirigen correctamente
a su ganador: 0 faltan, 0 apuntan al destino equivocado.

| Grupo | Gana | Redirigen hacia él |
|---|---|---|
| Bookkeeping vs. Accounting | **#133** (3.169 pal, score 71) | #310 |
| Security Deposit Accounting | **#210** (3.745 pal, score 79, 5 entrantes) | #212 (`...-best-practices-2`) |
| Chart of Accounts | **#221** (2.098 pal, score 70) | #219, #313 |
| What Is Trust Accounting | **#119** (3.148 pal, score 73, 13 entrantes) | #309 |
| Trust Accounting in QuickBooks | **#216** (2.569 pal, score 76, 5 entrantes) | #314 |

Comprobación literal de los seis:

```
  ya redirigen bien : 6
    #310 /property-management-bookkeeping-vs-accounting/ -> .../property-management-bookkeeping-vs-accounting-difference-what-you-need/
    #212 /security-deposit-accounting-property-managers-compliance-best-practices-2/ -> .../security-deposit-trust-account-reconciliation/
    #219 /property-management-chart-of-accounts-categories/ -> .../property-management-chart-of-accounts-setup-guide/
    #313 /setting-up-property-management-chart-of-accounts/ -> .../property-management-chart-of-accounts-setup-guide/
    #309 /what-is-trust-accounting-property-management/ -> .../what-is-trust-accounting-property-management-guide/
    #314 /quickbooks-trust-accounting-property-management/ -> .../trust-accounting-quickbooks-property-management/

  redirigen al destino equivocado : 0
  FALTA crear el 301 : 0
```

Y los 5 ganadores responden 200 con **canonical propio**, comprobado uno a uno.

---

## Lo que sí queda pendiente

### 1. El sitemap solo tiene 4 de los 32 posts publicados — es lo más grave del sitio

```
GET /post-sitemap.xml -> HTTP 200
  https://propertyledger.us/month-end-closing-checklist/            lastmod=2026-07-16
  https://propertyledger.us/owner-statements-explained/             lastmod=2026-07-16
  https://propertyledger.us/property-management-financial-statements/  lastmod=2026-07-16
  https://propertyledger.us/property-management-trust-accounting/   lastmod=2026-07-16
```

Son exactamente **los 4 posts que existían el 16 de julio**. Los 28 publicados desde entonces —
incluidos los 5 ganadores de la consolidación— **no están**. Google no está siendo informado del
80% del blog.

Lo que se descartó, con la medición:

- **No es caché del edge.** Con `?nocache=` el resultado es `cf-cache=MISS` y siguen siendo 4 URLs.
- **No es `noindex`.** Los excluidos rinden `robots = index, follow, max-snippet:-1, ...` igual que
  los incluidos, y su `rank_math_robots` en la base está vacío.
- **No es paginación.** `post-sitemap1.xml` devuelve las mismas 4; `post-sitemap2.xml` da 302.
- **No es configuración de Rank Math.** Leído en wp-admin: `Links Per Sitemap = 200`,
  `Exclude Posts` vacío, `Exclude Terms` vacío.
- **No es el autor.** Los 4 incluidos son de `plsadmin`, pero los posts de `plsadmin` del 6 al 10 de
  agosto (#228-#232) **tampoco están**. El corte es por fecha, no por autor.

Queda como hipótesis principal la **caché de sitemap que Rank Math guarda en la base de datos**,
congelada en el estado del 16 de julio y sin invalidarse al publicar. Encaja con que el `<lastmod>`
del índice sí sea del 14 de agosto (se calcula en vivo) mientras el contenido del post-sitemap es de
julio.

**Cómo comprobarlo y arreglarlo** (requiere wp-admin, es un cambio de ajustes → pendiente de tu visto bueno):

1. Rank Math → Ajustes de Sitemap → **Guardar cambios** sin tocar nada. Eso vacía la caché de sitemap.
2. Volver a pedir `post-sitemap.xml?nocache=1` y contar las URLs.
3. Si sigue en 4, desactivar temporalmente la caché de objetos/página y repetir.
4. Cuando salgan las ~26, reenviar el sitemap en Search Console (reenviarlo no consume cuota de
   indexación y da la mayor parte del valor).

### 2. Los posts redirigidos siguen en estado `publish`

Los 6 sirven un 301, pero siguen existiendo como publicados en WordPress. No es urgente —Google ve el
301— pero conviene pasarlos a papelera **después** de confirmar que el 301 lleva ≥ 30 días estable, y
solo entonces, para no perder la señal.

### 3. Cuatro enlaces internos apuntan a una URL redirigida

```
  post #310 -> /what-is-trust-accounting-property-management/   (debería ir a .../-guide/)
  post #313 -> /what-is-trust-accounting-property-management/
  post #314 -> /what-is-trust-accounting-property-management/
  post #316 -> /what-is-trust-accounting-property-management/
```

**Prioridad baja:** los cuatro orígenes (#310, #313, #314) son ellos mismos posts redirigidos, así
que su contenido no se sirve nunca. El único que importa es **#316**, que sí responde 200. De todas
formas la compuerta 9 reescribe los 301 al destino final en cada artículo nuevo.

---

## Qué haría, por orden

1. **Vaciar la caché de sitemap de Rank Math** y verificar que aparecen las ~26 URLs. Es lo que más
   pesa y no depende de nada más.
2. **Reenviar el sitemap en Search Console** una vez esté completo.
3. **Arreglar el enlace interno del post #316** al destino final.
4. **Dejar los 301 y los posts redirigidos como están** durante 30 días; después, papelera.
