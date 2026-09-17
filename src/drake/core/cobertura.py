"""Medición de cobertura de líneas con gcov.

`ReporteFuzzing.cobertura_lineas_porcentaje` nacía en 100.0 y nadie lo
asignaba nunca: el fuzzer informaba cobertura total incluso cuando sus
payloads no habían entrado en una sola rama del programa.

La cobertura importa justo acá: sin ella no se distingue "el programa aguantó
100 ejecuciones" de "las 100 ejecuciones salieron por el mismo `return` de
validación de entrada".
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# "Lines executed:72.41% of 29"
_LINEAS_EJECUTADAS = re.compile(r"Lines executed:\s*([\d.]+)%\s*of\s*(\d+)")

# Banderas de instrumentación: generan el .gcno al compilar y el .gcda al
# ejecutar el binario.
FLAGS_COBERTURA = ["--coverage"]


@dataclass
class MedicionCobertura:
    """Cobertura de líneas observada tras ejecutar el programa instrumentado."""
    medida: bool
    porcentaje: Optional[float] = None
    lineas_totales: Optional[int] = None
    motivo: str = ""

    @property
    def resumen(self) -> str:
        if not self.medida:
            return f"No medida: {self.motivo}"
        return f"{self.porcentaje:.1f} % de {self.lineas_totales} líneas ejecutables"


def medir_cobertura(archivo_c: Path, directorio_trabajo: Path) -> MedicionCobertura:
    """Corre gcov sobre los datos de perfilado dejados por las ejecuciones."""
    gcov = shutil.which("gcov")
    if not gcov:
        return MedicionCobertura(medida=False, motivo="gcov no está instalado.")

    # GCC nombra los datos de perfilado `<binario>-<fuente>.gcda`, así que hay
    # que pasarle a gcov el .gcda y no la ruta del fuente: apuntar al .c hace
    # que busque `<fuente>.gcno` junto al original y no encuentre nada.
    datos = sorted(directorio_trabajo.glob("*.gcda"))
    if not datos:
        return MedicionCobertura(
            medida=False,
            motivo="El programa no dejó datos de perfilado (.gcda); no se pudo instrumentar.",
        )

    try:
        res = subprocess.run(
            [gcov, "--no-output", *[str(d.name) for d in datos]],
            cwd=str(directorio_trabajo),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return MedicionCobertura(medida=False, motivo=f"No se pudo ejecutar gcov: {exc}")

    m = _LINEAS_EJECUTADAS.search(res.stdout or "")
    if not m:
        return MedicionCobertura(
            medida=False,
            motivo="gcov no informó líneas ejecutadas para este archivo.",
        )

    return MedicionCobertura(
        medida=True,
        porcentaje=float(m.group(1)),
        lineas_totales=int(m.group(2)),
    )
