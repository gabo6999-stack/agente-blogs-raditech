"""Regeneración determinista del JSON-LD FAQPage.

Corrige el bug reportado (FAQ JSON-LD mal formado): cuando el LLM redacta a mano
el bloque <script type="application/ld+json"> dentro del campo "content" (un JSON
anidado dentro de un string dentro de otro JSON), el escapado se rompe — faltan
comillas de cierre desde la 2a pregunta en adelante —, a veces queda metadata de
generación pegada tras </script>, y el schema no coincide con la FAQ visible, así
que Google Search Console no lo puede parsear.

Solución: no confiar en el JSON que escribe el modelo. Leer las preguntas y
respuestas VISIBLES del HTML (<h3>¿...?</h3> + el primer <p> siguiente), eliminar
cualquier <script ld+json> previo y TODO lo que le siga hasta el final (quita el
script roto + la metadata pegada), y reconstruir el schema con json.dumps, que
escapa correctamente TODAS las comillas de TODAS las entradas. Si no hay FAQ
visible, se devuelve el contenido SIN schema (mejor sin FAQ que con uno corrupto).

Módulo autónomo: solo depende de la stdlib (re, json, html) para poder probarse
sin importar anthropic/config.
"""
import re
import json
import html

_TAIL_LD_RE = re.compile(r'<script[^>]*application/ld\+json[\s\S]*$', re.IGNORECASE)
_H3_RE = re.compile(r'<h3[^>]*>([\s\S]*?)</h3>([\s\S]*?)(?=<h[23]\b|<script\b|$)', re.IGNORECASE)
_P_RE = re.compile(r'<p[^>]*>([\s\S]*?)</p>', re.IGNORECASE)


def _text(fragment: str) -> str:
    """Quita etiquetas HTML y decodifica entidades; normaliza espacios."""
    stripped = re.sub(r'<[^>]+>', '', fragment or '')
    return re.sub(r'\s+', ' ', html.unescape(stripped)).strip()


def extract_visible_faq(content: str) -> list:
    """Devuelve [{question, answer}, ...] leídos del HTML visible (antes de cualquier ld+json)."""
    if not content:
        return []
    has_ld = 'application/ld+json' in content.lower()
    visible = _TAIL_LD_RE.split(content, 1)[0] if has_ld else content
    faqs = []
    for m in _H3_RE.finditer(visible):
        question = _text(m.group(1))
        pm = _P_RE.search(m.group(2))
        if not pm:
            continue
        answer = _text(pm.group(1))
        if '?' in question and len(answer) > 20:
            faqs.append({"question": question, "answer": answer})
    return faqs


def rebuild_faq_jsonld(content: str) -> str:
    """Reemplaza el JSON-LD FAQPage del final por uno válido derivado de la FAQ visible.

    - Escapa correctamente TODAS las comillas de TODAS las entradas (json.dumps).
    - No deja metadata de generación tras </script> (se corta hasta EOF y se
      re-emite solo el script).
    - Valida implícitamente: json.dumps siempre produce JSON parseable.
    - El texto del JSON-LD coincide exactamente con la FAQ visible.
    - Si no hay FAQ visible, devuelve el contenido limpio SIN schema roto.
    """
    if not content:
        return content
    has_ld = 'application/ld+json' in content.lower()
    faqs = extract_visible_faq(content)
    # quitar cualquier ld+json previo + TODO lo que le siga (script roto + metadata pegada)
    cleaned = _TAIL_LD_RE.sub('', content).rstrip() if has_ld else content.rstrip()
    if not faqs:
        return cleaned
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f["question"],
                "acceptedAnswer": {"@type": "Answer", "text": f["answer"]},
            }
            for f in faqs
        ],
    }
    block = json.dumps(schema, ensure_ascii=False, indent=2)
    return cleaned + '\n<script type="application/ld+json">\n' + block + '\n</script>'
