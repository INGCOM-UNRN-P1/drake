"""Regresión de DRAKE-D0302: el fuzzing debe poder repetirse.

Se usaba el módulo global `random` sin semilla ni opción `--seed`: un crash
hallado en una corrida no se podía volver a provocar, y sin eso no hay manera
de confirmar que el arreglo lo resuelve.
"""

import random
import shutil
from pathlib import Path

import pytest

from drake.core.fuzzer import PAYLOADS_FRONTERA, ejecutar_fuzzing, generar_payload_mutado

necesita_gcc = pytest.mark.skipif(not shutil.which("gcc"), reason="requiere gcc")
INICIO = len(PAYLOADS_FRONTERA)


def _secuencia(semilla: int, cantidad: int = 40):
    rng = random.Random(semilla)
    return [generar_payload_mutado(i, rng) for i in range(INICIO, INICIO + cantidad)]


def test_la_misma_semilla_da_la_misma_secuencia():
    assert _secuencia(7) == _secuencia(7)


def test_otra_semilla_da_otra_secuencia():
    assert _secuencia(7) != _secuencia(8)


def test_los_payloads_de_frontera_no_dependen_de_la_semilla():
    for i, esperado in enumerate(PAYLOADS_FRONTERA):
        assert generar_payload_mutado(i, random.Random(1)) == esperado
        assert generar_payload_mutado(i, random.Random(2)) == esperado


@necesita_gcc
def test_el_reporte_registra_la_semilla_pedida(tmp_path):
    fuente = tmp_path / "eco.c"
    fuente.write_text("#include <stdio.h>\nint main(void){ return 0; }\n", encoding="utf-8")
    reporte = ejecutar_fuzzing(fuente, total_runs=3, seed=1234)
    assert reporte.semilla == 1234
    assert reporte.to_dict()["semilla"] == 1234


@necesita_gcc
def test_sin_semilla_se_elige_una_y_queda_registrada(tmp_path):
    """Para poder repetir una campaña de la que no se pidió semilla."""
    fuente = tmp_path / "eco.c"
    fuente.write_text("int main(void){ return 0; }\n", encoding="utf-8")
    reporte = ejecutar_fuzzing(fuente, total_runs=3)
    assert isinstance(reporte.semilla, int)
