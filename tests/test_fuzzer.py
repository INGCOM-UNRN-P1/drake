"""Tests unitarios para el fuzzer de DRAKE."""

from pathlib import Path
import pytest
from drake.core.fuzzer import ejecutar_fuzzing, generar_payload_mutado


def test_generar_payloads():
    p1 = generar_payload_mutado(0)
    p2 = generar_payload_mutado(4)
    assert isinstance(p1, str)
    assert isinstance(p2, str)


def test_fuzzing_programa_robusto(tmp_path):
    fuente = tmp_path / "robusto.c"
    fuente.write_text("""
    #include <stdio.h>
    int main(void) {
        int x;
        if (scanf("%d", &x) == 1) {
            printf("Leido: %d\\n", x);
        }
        return 0;
    }
    """)

    rep = ejecutar_fuzzing(fuente, total_runs=15)
    assert rep.ok is True
    assert rep.total_ejecuciones == 15
    assert rep.total_crashes == 0
