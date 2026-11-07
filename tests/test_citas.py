"""Prueba sin red: las marcas de cita de web_search no llegan al post (sanitize + G07g).

    python tests/test_citas.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gates.content import g07_valid_html  # noqa: E402
from tools.html_tools import sanitize  # noqa: E402

CASOS = {
    # tal como se publicó en cmlc #73: apertura rota y cierre normal
    'rota': ('<p>Con razón. (cite index="37-4"&gt;El ultrasonido no usa radiación</cite>, es seguro.</p>',
             '<p>Con razón. El ultrasonido no usa radiación, es seguro.</p>'),
    'rota_sin_escapar': ('<p>(cite index="5-5">Es un estudio</cite>.</p>', '<p>Es un estudio.</p>'),
    # tal como quedó en cmlc #17: par completo
    'par': ('<p>Detecta <cite index="2-1">lesiones óseas</cite> y más.</p>', '<p>Detecta lesiones óseas y más.</p>'),
    'escapada': ('<p>&lt;cite index="1-9"&gt;Según X&lt;/cite&gt; hoy.</p>', '<p>Según X hoy.</p>'),
    # no tocar palabras normales
    'palabra': ('<p>El médico lo solicite y lo cite.</p>', '<p>El médico lo solicite y lo cite.</p>'),
}

fallos = 0
for nombre, (entrada, esperado) in CASOS.items():
    limpio, _ = sanitize(entrada)
    ok = limpio == esperado
    g07g = next(r for r in g07_valid_html(limpio) if r.gate == 'G07g')
    print(f"[{'OK' if ok and g07g.passed else 'FALLA'}] {nombre}: {limpio!r}")
    fallos += (not ok) + (not g07g.passed)

# la compuerta bloquea si una marca llega sin sanear
crudo = '<p>(cite index="1-1"&gt;texto</cite></p>'
g = next(r for r in g07_valid_html(crudo) if r.gate == 'G07g')
print(f"[{'OK' if not g.passed and g.blocking else 'FALLA'}] G07g bloquea lo no saneado: {g.reason}")
fallos += g.passed or not g.blocking

print('RESULTADO:', 'todo OK' if not fallos else f'{fallos} fallo(s)')
sys.exit(1 if fallos else 0)
