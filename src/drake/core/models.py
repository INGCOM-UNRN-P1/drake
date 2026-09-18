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
    # Semilla de la campaña: con ella se reproduce exactamente la misma
    # secuencia de payloads (`drake fuzz --seed N`).
    semilla: Optional[int] = None
    # Nunca se asignaba: el reporte informaba 100 % de cobertura aunque los
    # payloads no hubieran entrado en ninguna rama. Ahora se completa con lo
    # que mide gcov, y `cobertura_medida` distingue el dato real del ausente.
    cobertura_lineas_porcentaje: Optional[float] = None
    cobertura_medida: bool = False
    cobertura_detalle: str = ""

    @property
    def ok(self) -> bool:
        return self.total_crashes == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "archivo": str(self.archivo),
            "ok": self.ok,
            "total_ejecuciones": self.total_ejecuciones,
            "total_crashes": self.total_crashes,
            "semilla": self.semilla,
            "cobertura_medida": self.cobertura_medida,
            "cobertura_lineas": (
                round(self.cobertura_lineas_porcentaje, 1)
                if self.cobertura_lineas_porcentaje is not None
                else None
            ),
            "cobertura_detalle": self.cobertura_detalle,
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
