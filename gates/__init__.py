"""Compuertas de bloqueo del agente de blogs.

Regla de la casa: es preferible NO publicar a publicar mal. Cada compuerta es
una funcion independiente que devuelve un GateResult con pasa/falla y motivo.
Si alguna falla, el post se queda en BORRADOR y se reporta por que.

Las compuertas corren en dos momentos:
  - PREFLIGHT: sobre el blog_data recien generado, antes de tocar WordPress.
  - POSTDRAFT: sobre el post ya creado como borrador en WordPress, antes de
    promoverlo a publicado (es donde viven la comprobacion de slug real, la
    categoria asignada y la puntuacion de Rank Math leida del editor).
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GateResult:
    gate: str                      # id corto, p.ej. "G05"
    name: str                      # nombre legible
    passed: bool
    reason: str = ""               # por que fallo (o nota si paso)
    details: Any = field(default=None)   # evidencia cruda para el reporte
    blocking: bool = True          # si False, se reporta pero no detiene

    @property
    def status(self) -> str:
        if self.passed:
            return "PASA"
        return "FALLA" if self.blocking else "AVISO"

    def __str__(self):
        return f"[{self.gate}] {self.status}: {self.name}" + (f" — {self.reason}" if self.reason else "")


class GateReport:
    """Coleccion de resultados de una corrida."""

    def __init__(self, site_key: str, topic: str = ""):
        self.site_key = site_key
        self.topic = topic
        self.results: list[GateResult] = []

    def add(self, result: GateResult) -> GateResult:
        self.results.append(result)
        print(f"  {result}")
        return result

    def extend(self, results: list[GateResult]):
        for r in results:
            self.add(r)

    @property
    def blocking_failures(self) -> list[GateResult]:
        return [r for r in self.results if not r.passed and r.blocking]

    @property
    def ok(self) -> bool:
        return not self.blocking_failures

    def summary(self) -> str:
        p = sum(1 for r in self.results if r.passed)
        return f"{p}/{len(self.results)} compuertas pasadas" + (
            "" if self.ok else f" — BLOQUEAN: {', '.join(r.gate for r in self.blocking_failures)}")

    def to_dict(self) -> dict:
        return {
            "site": self.site_key,
            "topic": self.topic,
            "ok": self.ok,
            "summary": self.summary(),
            "gates": [{"gate": r.gate, "name": r.name, "status": r.status,
                       "passed": r.passed, "blocking": r.blocking,
                       "reason": r.reason, "details": r.details}
                      for r in self.results],
        }
