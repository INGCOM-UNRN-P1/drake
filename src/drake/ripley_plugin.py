"""Plugin de DRAKE para integración con RIPLEY."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any, Dict, List

from drake.core.fuzzer import ejecutar_fuzzing

_MAIN = re.compile(r"\bmain\s*\(")


def _programas(workspace: Path, manifest_config: Dict[str, Any]) -> List[Path]:
    """Archivos C que son programas completos (definen `main`).

    Un módulo sin `main` no enlaza: fuzzearlo daba un error de compilación que
    llegaba como hallazgo, y el plugin tomaba el primer archivo del glob sin mirar.
    """
    if manifest_config.get("c_files"):
        candidatos = [Path(f) for f in manifest_config["c_files"]]
    elif workspace.is_file():
        candidatos = [workspace]
    else:
        candidatos = sorted(workspace.glob("*.c")) + sorted(workspace.glob("src/*.c"))
    programas = []
    for candidato in candidatos:
        try:
            if _MAIN.search(candidato.read_text(encoding="utf-8", errors="replace")):
                programas.append(candidato)
        except OSError:
            continue
    return programas


class DrakePlugin:
    """Plugin de fuzzing y testeo con límites para Ripley."""

    name = "fuzzing"
    version = "0.1.0"

    def is_available(self) -> bool:
        # Fuzzear compila el programa: sin gcc no hay nada que ejecutar.
        return shutil.which("gcc") is not None

    def execute(self, workspace: Path, manifest_config: Dict[str, Any]) -> Dict[str, Any]:
        programas = _programas(workspace, manifest_config)
        if not programas:
            return {"ok": True, "total_runs": 0, "total_crashes": 0, "observaciones": []}

        runs = int(manifest_config.get("runs", 30))
        observaciones = []
        total_runs = 0
        total_crashes = 0
        ok = True

        for programa in programas:
            rep = ejecutar_fuzzing(programa, total_runs=runs)
            ok = ok and rep.ok
            total_runs += rep.total_ejecuciones
            total_crashes += rep.total_crashes
            for c in rep.crashes:
                observaciones.append({
                    "codigo": f"FUZZ_CRASH_{c.senal_error or 'FAIL'}",
                    "severidad": "ERROR",
                    "archivo": str(programa),
                    "mensaje": f"Fuzzing provocó un crash ({c.senal_error}) con el payload: {repr(c.payload_input[:30])}",
                })

        return {
            "ok": ok,
            "total_runs": total_runs,
            "total_crashes": total_crashes,
            "observaciones": observaciones,
        }
