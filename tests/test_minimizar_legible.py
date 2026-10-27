"""Ola 13 (QoL #264): la entrada mínima privilegia enteros chicos y texto legible."""

import shutil
import subprocess
from pathlib import Path

import pytest

from drake.core.fuzzer import minimizar_entrada

con_gcc = pytest.mark.skipif(shutil.which("gcc") is None, reason="hace falta gcc")

# Se cae (SIGSEGV) cuando el primer entero es mayor que 50, sea cual sea el resto de la entrada.
UMBRAL = """#include <stdio.h>
int main(void)
{
    int n = 0;
    if (scanf("%d", &n) != 1)
    {
        return 0;
    }
    if (n > 50)
    {
        int *p = NULL;
        return *p;
    }
    printf("%d\\n", n);
    return 0;
}
"""


@pytest.fixture
def umbral(tmp_path: Path) -> Path:
    fuente = tmp_path / "umbral.c"
    fuente.write_text(UMBRAL, encoding="utf-8")
    binario = tmp_path / "umbral"
    subprocess.run(["gcc", "-O0", str(fuente), "-o", str(binario)], check=True)
    return binario


@con_gcc
def test_el_entero_se_achica_hasta_el_borde_y_se_va_la_basura(umbral):
    entrada = "73920 \x00\x01zz%s%s\notra linea 99999\n"
    assert "\x00" in entrada
    minima = minimizar_entrada(umbral, entrada, "SIGSEGV")
    assert minima == "51\n"  # el borde exacto (no 72 ni 73920), con su salto de línea
    assert all(c.isprintable() or c in "\n\t" for c in minima)
    assert "otra linea" not in minima


def test_criterio_propio_y_rachas():
    # Sin binario: falla si hay al menos 7 'A' seguidas y un 3 (por ejemplo, un búfer y un índice).
    def falla(texto: str) -> bool:
        return "A" * 7 in texto and "3" in texto

    minima = minimizar_entrada(Path("/no/existe"), "x " + "A" * 4096 + " 1234567 y\n", "-", falla=falla)
    assert "A" * 7 in minima and "A" * 8 not in minima
    assert "1234567" not in minima and "3" in minima
