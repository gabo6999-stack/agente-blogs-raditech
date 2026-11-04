"""Prueba sin red de pick_category. Ejecutar: python tests/test_categories.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SITES
from tools.categories import pick_category

CASOS_CMLC = [
    ("rayos x a domicilio", "Rayos X"),
    ("panorámica dental Mazatlán", "Panorámica dental"),
    ("preparación para tomografía", "Tomografía"),
    ("ultrasonido obstétrico Mazatlán", "Ultrasonido"),
    ("BI-RADS actualización 2026", "Mastografía"),
    ("mamografía vs mastografía", "Mastografía"),
    ("qué es una densitometría ósea", "Otros estudios"),
    ("cómo elegir un centro de radiología", "Radiología e Imagen"),
    ("contacto y tactil: horarios del centro", "Radiología e Imagen"),
]


def main() -> int:
    fallos = 0
    for tema, esperado in CASOS_CMLC:
        got = pick_category("cmlc", tema, "", tema)
        ok = got == esperado
        fallos += not ok
        print(f"[{'OK' if ok else 'FALLA'}] cmlc: {tema!r} -> {got} (esperado {esperado})")

    # El título/keyword también cuentan, no solo el tema.
    got = pick_category("cmlc", "", "ecografía Mazatlán", "Guía")
    ok = got == "Ultrasonido"
    fallos += not ok
    print(f"[{'OK' if ok else 'FALLA'}] cmlc: keyword 'ecografía' -> {got}")

    # Sitios sin reglas: igual que el flujo anterior (categoría del redactor o del sitio).
    for key in ("raditech", "tnrvisual", "propertyledger"):
        assert not SITES[key].get("category_rules"), key
        for propuesta in ("Mi categoría", ""):
            esperado = propuesta or SITES[key]["category"]
            got = pick_category(key, "rayos x tomografía", "mastografía", "t", propuesta)
            ok = got == esperado
            fallos += not ok
            print(f"[{'OK' if ok else 'FALLA'}] {key}: propuesta={propuesta!r} -> {got}")

    print("RESULTADO:", "todo OK" if not fallos else f"{fallos} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
