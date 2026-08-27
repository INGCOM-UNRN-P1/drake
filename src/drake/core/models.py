"""Modelos de datos para el motor de fuzzing y cobertura en DRAKE."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class CasoFuzz:
    id_caso: int
    payload_input: str
    codigo_retorno: int
    es_crash: bool
    tiempo_ms: float
    senal_error: Optional[str] = None


@dataclass
class ReporteFuzzing:
    archivo: Path
    total_ejecuciones: int
    total_crashes: int
    crashes: List[CasoFuzz] = field(default_factory=list)
    cobertura_lineas_porcentaje: float = 100.0

    @property
    def ok(self) -> bool:
        return self.total_crashes == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "archivo": str(self.archivo),
            "ok": self.ok,
            "total_ejecuciones": self.total_ejecuciones,
            "total_crashes": self.total_crashes,
            "cobertura_lineas": round(self.cobertura_lineas_porcentaje, 1),
            "crashes": [
                {
                    "id": c.id_caso,
                    "payload": c.payload_input[:100],
                    "codigo_retorno": c.codigo_retorno,
                    "senal": c.senal_error,
                }
                for c in self.crashes[:10]
            ],
        }
