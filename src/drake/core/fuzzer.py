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
    except ImportError:
        return None  # sin el extra `ecosistema` se usa el camino propio
    res = compilar_archivos([archivo_c], binario_salida=binario, flags_adicionales=["-g", "-O0", *FLAGS_COBERTURA])
    return res.exito, res.codigo_retorno, res.stderr_crudo


def _senal(binario: Path, entrada: str, timeout: float) -> Optional[str]:
    """La señal con la que termina el programa para esa entrada (None si no falla)."""
    try:
        res = subprocess.run([str(binario.resolve())], input=entrada, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None
    ret = res.returncode
    if ret < 0:
        return {11: "SIGSEGV", 6: "SIGABRT", 8: "SIGFPE"}.get(-ret, f"SIGNAL_{-ret}")
    if ret > 128:
        return f"SIGNAL_{ret - 128}"
    return None


def minimizar_entrada(binario: Path, entrada: str, senal: str, timeout: float = 1.0, max_pruebas: int = 300) -> str:
    """La entrada más chica que provoca la misma señal (delta debugging, primero por líneas y
    después por caracteres): con 4096 «A» el estudiante no ve qué falla; con 12, sí."""
    actual = entrada
    pruebas = 0
    for separar, unir in ((lambda t: t.splitlines(keepends=True), "".join), (list, "".join)):
        partes = separar(actual)
        n = 2
        while len(partes) >= 2 and pruebas < max_pruebas:
            tam = max(1, len(partes) // n)
            redujo = False
            for i in range(0, len(partes), tam):
                candidato = partes[:i] + partes[i + tam:]
                pruebas += 1
                if candidato and _senal(binario, unir(candidato), timeout) == senal:
                    partes, n, redujo = candidato, max(n - 1, 2), True
                    break
                if pruebas >= max_pruebas:
                    break
            if not redujo:
                if tam == 1:
                    break
                n = min(len(partes), n * 2)
        actual = unir(partes)
    return actual


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
        timeouts: List[CasoFuzz] = []

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
                timeouts.append(CasoFuzz(i + 1, payload, 124, False, t_ms, "TIMEOUT"))
            except Exception as e:
                t_ms = (time.perf_counter() - t0) * 1000.0
                crashes.append(CasoFuzz(i + 1, payload, 1, True, t_ms, str(e)))

        # Una entrada mínima por cada tipo de falla (con el binario todavía disponible).
        minimizadas: dict = {}
        for c in crashes:
            if c.senal_error and c.senal_error.startswith("SIG") and c.payload_input:
                if c.senal_error not in minimizadas:
                    minimizadas[c.senal_error] = minimizar_entrada(binario, c.payload_input, c.senal_error,
                                                                   timeout_por_run)
                c.payload_minimo = minimizadas[c.senal_error]

        cobertura = medir_cobertura(archivo_c, tmp_path)

        return ReporteFuzzing(
            archivo=archivo_c,
            total_ejecuciones=total_runs,
            total_crashes=len(crashes),
            crashes=crashes,
            timeouts=timeouts,
            semilla=seed,
            cobertura_lineas_porcentaje=cobertura.porcentaje,
            cobertura_medida=cobertura.medida,
            cobertura_detalle=cobertura.resumen,
        )


def guardar_casos(reporte: ReporteFuzzing, directorio: Path, modelo: Optional[Path] = None) -> List[Path]:
    """Guarda cada entrada mínima que hace fallar al programa como caso de nostromo (crash_NN.in).

    Con la solución modelo, también la salida esperada (crash_NN.out): así el caso queda en la suite
    y el arreglo del estudiante se puede verificar. Sin modelo solo se escribe la entrada.
    """
    from drake.core.generar_casos import compilar_modelo, ejecutar_modelo

    entradas: List[str] = []
    for c in reporte.crashes:
        minima = c.payload_minimo or c.payload_input
        if minima and minima not in entradas:
            entradas.append(minima)
    directorio.mkdir(parents=True, exist_ok=True)
    escritos: List[Path] = []
    with tempfile.TemporaryDirectory() as tmp:
        binario = None
        if modelo is not None:
            binario = Path(tmp) / "modelo.bin"
            ok, err, _ = compilar_modelo(modelo, binario)
            if not ok:
                raise RuntimeError(f"No se pudo compilar el modelo: {err}")
        for n, entrada in enumerate(entradas, 1):
            ruta_in = directorio / f"crash_{n:02d}.in"
            ruta_in.write_text(entrada, encoding="utf-8")
            escritos.append(ruta_in)
            if binario is not None:
                _, salida = ejecutar_modelo(binario, entrada)
                ruta_out = ruta_in.with_suffix(".out")
                ruta_out.write_text(salida, encoding="utf-8")
                escritos.append(ruta_out)
    return escritos

