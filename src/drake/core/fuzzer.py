"""Motor de generación de casos de prueba aleatorios y ejecución de fuzzing en DRAKE."""

from __future__ import annotations

import random
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Tuple

from drake.core.cobertura import FLAGS_COBERTURA, medir_cobertura
from drake.core.models import CasoFuzz, ReporteFuzzing

PAYLOADS_FRONTERA = [
    "",
    "0\n",
    "-1\n",
    "1\n",
    "2147483647\n",       # INT_MAX
    "-2147483648\n",      # INT_MIN
    "4294967295\n",       # UINT_MAX
    "A" * 1024 + "\n",    # Búfer largo
    "A" * 4096 + "\n",
    "%s%s%s%s%s\n",       # Format string
    "0 0 0 0\n",
    "\x00\n",
    "\n\n\n\n",
]


def generar_payload_mutado(iteracion: int, rng: Optional[random.Random] = None) -> str:
    """Genera un payload de entrada con mutaciones aleatorias y casos límite.

    Con un `rng` sembrado la secuencia es reproducible. Antes se usaba el
    módulo global `random` sin semilla: un crash encontrado en una corrida no se
    podía volver a provocar, y sin eso no se puede confirmar que el arreglo
    del estudiante lo resuelve.
    """
    if iteracion < len(PAYLOADS_FRONTERA):
        return PAYLOADS_FRONTERA[iteracion]

    rng = rng or random.Random()
    tipo = rng.choice(["int_random", "string_random", "mixed"])
    if tipo == "int_random":
        nums = [str(rng.randint(-100000, 100000)) for _ in range(rng.randint(1, 5))]
        return " ".join(nums) + "\n"
    elif tipo == "string_random":
        caracteres = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \t\n!@#$%^&*()"
        largo = rng.randint(1, 256)
        return "".join(rng.choice(caracteres) for _ in range(largo)) + "\n"
    else:
        return f"{rng.randint(-100, 100)} {'X' * rng.randint(10, 100)}\n"


def _compilar_con_daedalus(archivo_c: Path, binario: Path) -> Optional[Tuple[bool, int, str]]:
    try:
        from daedalus.core.compiler import compilar_archivos
        res = compilar_archivos([archivo_c], binario_salida=binario, flags_adicionales=["-g", "-O0", *FLAGS_COBERTURA])
        return res.exito, res.codigo_retorno, res.stderr_crudo
    except ImportError:
        import sys
        sibling = Path(__file__).resolve().parents[4] / "daedalus" / "src"
        if sibling.is_dir() and str(sibling) not in sys.path:
            sys.path.insert(0, str(sibling))
            try:
                from daedalus.core.compiler import compilar_archivos
                res = compilar_archivos([archivo_c], binario_salida=binario, flags_adicionales=["-g", "-O0", *FLAGS_COBERTURA])
                return res.exito, res.codigo_retorno, res.stderr_crudo
            except ImportError:
                return None
        return None


def ejecutar_fuzzing(
    archivo_c: Path,
    total_runs: int = 50,
    timeout_por_run: float = 1.0,
    seed: Optional[int] = None,
) -> ReporteFuzzing:
    """Compila el programa y ejecuta múltiples corridas con payloads de fuzzing.

    Sin `seed` se elige una al azar, pero siempre queda registrada en el reporte
    para poder repetir exactamente la misma campaña con `--seed`.
    """
    archivo_c = Path(archivo_c)
    if seed is None:
        seed = random.SystemRandom().randrange(2**32)
    rng = random.Random(seed)
    if not archivo_c.is_file():
        raise FileNotFoundError(f"No se encontró el archivo: {archivo_c}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        binario = tmp_path / "prog_fuzz"

        daed_res = _compilar_con_daedalus(archivo_c, binario)
        if daed_res is not None:
            ok, rc, stderr = daed_res
            if not ok:
                return ReporteFuzzing(
                    archivo=archivo_c,
                    total_ejecuciones=0,
                    total_crashes=1,
                    crashes=[CasoFuzz(1, "", rc, True, 0.0, "COMPILATION_ERROR")],
                )
        else:
            gcc = shutil.which("gcc") or "gcc"
            res_comp = subprocess.run(
                [gcc, "-g", "-O0", *FLAGS_COBERTURA, str(archivo_c.resolve()), "-o", str(binario.resolve()), "-lm"],
                capture_output=True,
                text=True,
            )
            if res_comp.returncode != 0:
                return ReporteFuzzing(
                    archivo=archivo_c,
                    total_ejecuciones=0,
                    total_crashes=1,
                    crashes=[CasoFuzz(1, "", res_comp.returncode, True, 0.0, "COMPILATION_ERROR")],
                )

        crashes: List[CasoFuzz] = []

        for i in range(total_runs):
            payload = generar_payload_mutado(i, rng)
            t0 = time.perf_counter()
            try:
                res = subprocess.run(
                    [str(binario.resolve())],
                    input=payload,
                    capture_output=True,
                    text=True,
                    timeout=timeout_por_run,
                )
                t_ms = (time.perf_counter() - t0) * 1000.0
                ret = res.returncode

                if ret < 0:
                    sig = -ret
                    sig_name = "SIGSEGV" if sig == 11 else "SIGABRT" if sig == 6 else "SIGFPE" if sig == 8 else f"SIGNAL_{sig}"
                    crashes.append(CasoFuzz(i + 1, payload, ret, True, t_ms, sig_name))
                elif ret > 128:
                    crashes.append(CasoFuzz(i + 1, payload, ret, True, t_ms, f"SIGNAL_{ret - 128}"))

            except subprocess.TimeoutExpired:
                t_ms = (time.perf_counter() - t0) * 1000.0
                crashes.append(CasoFuzz(i + 1, payload, 124, True, t_ms, "TIMEOUT"))
            except Exception as e:
                t_ms = (time.perf_counter() - t0) * 1000.0
                crashes.append(CasoFuzz(i + 1, payload, 1, True, t_ms, str(e)))

        cobertura = medir_cobertura(archivo_c, tmp_path)

        return ReporteFuzzing(
            archivo=archivo_c,
            total_ejecuciones=total_runs,
            total_crashes=len(crashes),
            crashes=crashes,
            semilla=seed,
            cobertura_lineas_porcentaje=cobertura.porcentaje,
            cobertura_medida=cobertura.medida,
            cobertura_detalle=cobertura.resumen,
        )
