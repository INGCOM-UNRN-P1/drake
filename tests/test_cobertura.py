"""Regresión de DRAKE-D0301: la cobertura debe medirse, no venir en 100 %."""

import shutil
from pathlib import Path

import pytest

from drake.core.cobertura import MedicionCobertura, medir_cobertura
from drake.core.fuzzer import ejecutar_fuzzing

# Programa con ramas que solo se alcanzan con una entrada muy específica: el
# fuzzer por límites no debería llegar a ellas, y la cobertura tiene que
# reflejarlo.
PROGRAMA = """#include <stdio.h>
#include <string.h>
int main(void) {
    char buf[64];
    if (!fgets(buf, sizeof(buf), stdin)) { return 0; }
    if (strncmp(buf, "MAGIA", 5) == 0) {
        printf("rama profunda 1\\n");
        if (buf[5] == 'X') { printf("rama profunda 2\\n"); }
        else { printf("rama profunda 3\\n"); }
    } else {
        printf("rama comun\\n");
    }
    return 0;
}
"""

necesita_toolchain = pytest.mark.skipif(
    not (shutil.which("gcc") and shutil.which("gcov")),
    reason="requiere gcc y gcov",
)


@pytest.fixture
def fuente(tmp_path):
    ruta = tmp_path / "objetivo.c"
    ruta.write_text(PROGRAMA, encoding="utf-8")
    return ruta


@necesita_toolchain
def test_la_cobertura_es_real_y_no_del_cien_por_ciento(fuente):
    reporte = ejecutar_fuzzing(fuente, total_runs=10)
    assert reporte.cobertura_medida is True
    assert reporte.cobertura_lineas_porcentaje is not None
    # Las ramas tras `MAGIA` quedan sin visitar: no puede dar 100 %.
    assert reporte.cobertura_lineas_porcentaje < 100.0


@necesita_toolchain
def test_el_json_expone_la_cobertura_medida(fuente):
    datos = ejecutar_fuzzing(fuente, total_runs=10).to_dict()
    assert datos["cobertura_medida"] is True
    assert 0.0 < datos["cobertura_lineas"] < 100.0
    assert "líneas ejecutables" in datos["cobertura_detalle"]


def test_sin_gcov_se_declara_no_medida(tmp_path, monkeypatch):
    monkeypatch.setattr("drake.core.cobertura.shutil.which", lambda _: None)
    medicion = medir_cobertura(tmp_path / "x.c", tmp_path)
    assert medicion.medida is False
    assert medicion.resumen.startswith("No medida:")


def test_sin_datos_de_perfilado_se_declara_no_medida(tmp_path):
    medicion = medir_cobertura(tmp_path / "x.c", tmp_path)
    assert medicion.medida is False


def test_resumen_de_una_medicion_real():
    medicion = MedicionCobertura(medida=True, porcentaje=62.5, lineas_totales=8)
    assert medicion.resumen == "62.5 % de 8 líneas ejecutables"
