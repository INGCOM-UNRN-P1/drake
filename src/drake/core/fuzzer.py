"""Motor de generación de casos de prueba aleatorios y ejecución de fuzzing en DRAKE."""

from __future__ import annotations

import random
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

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


def _ddmin(partes: List[str], falla: Callable[[str], bool]) -> List[str]:
    """Delta debugging: quita trozos de `partes` mientras la entrada que quede siga fallando."""
    n = 2
    while len(partes) >= 2:
        tam = max(1, len(partes) // n)
        redujo = False
        for i in range(0, len(partes), tam):
            candidato = partes[:i] + partes[i + tam:]
            if candidato and falla("".join(candidato)):
                partes, n, redujo = candidato, max(n - 1, 2), True
                break
        if not redujo:
            if tam == 1:
                break
            n = min(len(partes), n * 2)
    return partes


_RE_NUMERO = re.compile(r"-?\d+")


def _numeros_chicos(texto: str, falla: Callable[[str], bool]) -> str:
    """Cada entero, por el más chico que mantiene la falla: 0, 1, -1, 2… o la mitad (QoL #264)."""
    inicio = 0
    while True:
        m = _RE_NUMERO.search(texto, inicio)
        if not m:
            return texto
        valor = int(m[0])
        candidatos = [0, 1, -1, 2, -2, 10, -10, 100]
        mitad = valor
        while abs(mitad) > 1:
            mitad //= 2
            candidatos.append(mitad)
        antes, despues = texto[:m.start()], texto[m.end():]

        def con(v: int, antes: str = antes, despues: str = despues) -> str:
            return antes + str(v) + despues

        elegido = valor
        sin_falla: Optional[int] = None  # el mayor candidato (en valor absoluto) que no falló
        for c in sorted({c for c in candidatos if abs(c) < abs(valor)}, key=lambda c: (abs(c), c < 0)):
            if falla(con(c)):
                elegido = c
                break
            if (c >= 0) == (valor >= 0):
                sin_falla = c
        # Si falla con 72 y no con 36, el borde está en el medio: se busca por bisección (51 dice
        # más que 72). Cada paso se verifica, así que el resultado siempre sigue fallando.
        if sin_falla is not None and (elegido >= 0) == (sin_falla >= 0) and abs(elegido) - abs(sin_falla) > 1:
            bajo, alto = abs(sin_falla) + 1, abs(elegido)
            signo = -1 if elegido < 0 else 1
            while bajo < alto:
                medio = (bajo + alto) // 2
                if falla(con(signo * medio)):
                    alto = medio
                else:
                    bajo = medio + 1
            elegido = signo * alto
        reemplazo = str(elegido)
        texto = con(elegido)
        inicio = m.start() + len(reemplazo)


def _imprimibles(texto: str, falla: Callable[[str], bool]) -> str:
    """Los bytes nulos y de control (salvo salto de línea y tabulación) se borran o pasan a 'a'."""
    i = 0
    while i < len(texto):
        c = texto[i]
        if c.isprintable() or c in "\n\t":
            i += 1
            continue
        for reemplazo in ("", "a"):
            prueba = texto[:i] + reemplazo + texto[i + 1:]
            if falla(prueba):
                texto = prueba
                break
        else:
            i += 1
            continue
        i += len(reemplazo)
    return texto


def _acortar_rachas(texto: str, falla: Callable[[str], bool]) -> str:
    """Una racha del mismo carácter (4096 «A») se acorta al largo mínimo que sigue fallando."""
    inicio = 0
    while True:
        m = re.compile(r"(.)\1{3,}", re.S).search(texto, inicio)
        if not m:
            return texto
        bajo, alto = 1, len(m[0])  # el largo `alto` falla; se busca el menor que también falle
        while bajo < alto:
            medio = (bajo + alto) // 2
            if falla(texto[:m.start()] + m[1] * medio + texto[m.end():]):
                alto = medio
            else:
                bajo = medio + 1
        texto = texto[:m.start()] + m[1] * alto + texto[m.end():]
        inicio = m.start() + alto


def _no_termina(binario: Path, entrada: str, timeout: float) -> bool:
    try:
        subprocess.run([str(binario.resolve())], input=entrada, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return True
    except OSError:
        return False
    return False


def minimizar_entrada(binario: Path, entrada: str, senal: str, timeout: float = 1.0, max_pruebas: int = 300,
                      falla: Optional[Callable[[str], bool]] = None) -> str:
    """La entrada más chica y legible que provoca la misma señal (QoL #264): con 4096 «A» el estudiante
    no ve qué falla; con 15, sí.

    Por fases, cada una sin perder la falla: quita líneas y después palabras (delta debugging),
    achica los enteros (0, 1, -1… antes que 2147483647), borra o reemplaza por 'a' los bytes
    nulos y de control, y acorta las rachas del mismo carácter. No recorta carácter por carácter:
    eso partía números y juntaba palabras en algo ilegible. `falla` reemplaza el criterio (por
    ejemplo, «no termina a tiempo»).
    """
    pruebas = [0]

    def sigue_fallando(candidato: str) -> bool:
        if not candidato or pruebas[0] >= max_pruebas:
            return False
        pruebas[0] += 1
        if falla is not None:
            return falla(candidato)
        return _senal(binario, candidato, timeout) == senal

    actual = "".join(_ddmin(entrada.splitlines(keepends=True), sigue_fallando))
    actual = "".join(_ddmin(re.findall(r"\S+\s*|\s+", actual), sigue_fallando))
    actual = _numeros_chicos(actual, sigue_fallando)
    actual = _imprimibles(actual, sigue_fallando)
    actual = _acortar_rachas(actual, sigue_fallando)
    # Un .in termina en un salto de línea, sin espacios colgando, si eso no cambia la falla.
    canonica = actual.rstrip() + "\n"
    if canonica != actual and sigue_fallando(canonica):
        return canonica
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
        # También el primer timeout: cada prueba espera el timeout entero, así que con pocas pruebas.
        if timeouts and timeouts[0].payload_input:
            minima = minimizar_entrada(binario, timeouts[0].payload_input, "TIMEOUT", timeout_por_run, max_pruebas=25,
                                       falla=lambda e: _no_termina(binario, e, timeout_por_run))
            for t in timeouts:  # como con las señales: todos los timeouts son la misma falla
                t.payload_minimo = minima

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


@dataclass
class CasosGuardados:
    escritos: List[Path] = field(default_factory=list)
    ya_estaban: int = 0  # entradas que la suite ya tenía (con cualquier nombre)
    descartados: List[str] = field(default_factory=list)  # entradas con las que el modelo tampoco anda


_RE_CASO_DRAKE = re.compile(r"^crash_(\d+)$")


def guardar_casos(reporte: ReporteFuzzing, directorio: Path, modelo: Optional[Path] = None) -> CasosGuardados:
    """Agrega a la suite de regresión del TP cada entrada mínima que hace fallar al programa (Ola 13).

    Cada caso queda como `crash_NN.in` con `crash_NN.tags` («regresion drake SIGSEGV» o «timeout»:
    `nostromo test prog tests/ --etiqueta regresion` corre sólo esos). Con la solución modelo se
    escribe también `crash_NN.out`, y sólo entran los casos que el modelo supera (termina con 0, que es
    lo que exige nostromo): uno en el que el modelo también falla no sirve de regresión. La numeración
    sigue después de los `crash_NN` que ya hay y no se repite una entrada que la suite ya tenga, así que
    correr drake de nuevo no pisa ni duplica casos.
    """
    from drake.core.generar_casos import compilar_modelo, ejecutar_modelo

    entradas: List[Tuple[str, str]] = []
    for c in [*reporte.crashes, *reporte.timeouts]:
        minima = c.payload_minimo or c.payload_input
        if c.senal_error == "COMPILATION_ERROR" or not minima or any(minima == e for e, _ in entradas):
            continue
        entradas.append((minima, "timeout" if c.senal_error == "TIMEOUT" else (c.senal_error or "crash")))
    directorio.mkdir(parents=True, exist_ok=True)
    existentes = {p.read_text(encoding="utf-8", errors="replace") for p in directorio.glob("*.in")}
    numeros = [int(m[1]) for p in directorio.glob("crash_*.in") if (m := _RE_CASO_DRAKE.match(p.stem))]
    siguiente = max(numeros, default=0) + 1
    resultado = CasosGuardados()
    with tempfile.TemporaryDirectory() as tmp:
        binario = None
        if modelo is not None:
            binario = Path(tmp) / "modelo.bin"
            ok, err, _ = compilar_modelo(modelo, binario)
            if not ok:
                raise RuntimeError(f"No se pudo compilar el modelo: {err}")
        for entrada, motivo in entradas:
            if entrada in existentes:
                resultado.ya_estaban += 1
                continue
            salida = None
            if binario is not None:
                rc, salida = ejecutar_modelo(binario, entrada)
                if rc != 0:
                    detalle = "no termina" if rc == 124 else f"termina con código {rc}"
                    resultado.descartados.append(f"{entrada[:40]!r}: el modelo también {detalle}")
                    continue
            ruta_in = directorio / f"crash_{siguiente:02d}.in"
            ruta_in.write_text(entrada, encoding="utf-8")
            ruta_in.with_suffix(".tags").write_text(f"regresion drake {motivo}\n", encoding="utf-8")
            resultado.escritos += [ruta_in, ruta_in.with_suffix(".tags")]
            if salida is not None:
                ruta_in.with_suffix(".out").write_text(salida, encoding="utf-8")
                resultado.escritos.append(ruta_in.with_suffix(".out"))
            existentes.add(entrada)
            siguiente += 1
    return resultado
