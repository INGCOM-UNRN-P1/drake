"""Plugin de DRAKE para integración con RIPLEY."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from drake.core.fuzzer import ejecutar_fuzzing


class DrakePlugin:
    """Plugin de fuzzing y testeo con límites para Ripley."""

    name = "fuzzing"
    version = "0.1.0"

    def is_available(self) -> bool:
        return True

    def execute(self, workspace: Path, manifest_config: Dict[str, Any]) -> Dict[str, Any]:
        archivos = list(workspace.glob("*.c")) + list(workspace.glob("src/*.c"))
        if not archivos:
            return {"ok": True, "total_runs": 0, "observaciones": []}

        rep = ejecutar_fuzzing(archivos[0], total_runs=30)
        observaciones = []

        for c in rep.crashes:
            observaciones.append({
                "codigo": f"FUZZ_CRASH_{c.senal_error or 'FAIL'}",
                "severidad": "ERROR",
                "archivo": str(archivos[0]),
                "mensaje": f"Fuzzing provocó un crash ({c.senal_error}) con el payload: {repr(c.payload_input[:30])}",
            })

        return {
            "ok": rep.ok,
            "total_runs": rep.total_ejecuciones,
            "total_crashes": rep.total_crashes,
            "observaciones": observaciones,
        }
