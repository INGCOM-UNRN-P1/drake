"""Ola 13 (QoL #264, #973): lo que drake encuentra queda como suite de regresión lista para nostromo."""

import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from drake.cli import app
from drake.core.fuzzer import ejecutar_fuzzing, guardar_casos

runner = CliRunner()
con_gcc = pytest.mark.skipif(shutil.which("gcc") is None, reason="hace falta gcc")

# Se cae con un entero mayor que 50 y se cuelga con uno negativo.
FRAGIL = """#include <stdio.h>
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
    while (n < 0)
    {
    }
    printf("%d\\n", n * 2);
    return 0;
}
"""
MODELO = """#include <stdio.h>
int main(void)
{
    int n = 0;
    if (scanf("%d", &n) == 1)
    {
        printf("%d\\n", n * 2);
    }
    return 0;
}
"""


@pytest.fixture
def fuentes(tmp_path: Path):
    fragil = tmp_path / "fragil.c"
    fragil.write_text(FRAGIL, encoding="utf-8")
    modelo = tmp_path / "modelo.c"
    modelo.write_text(MODELO, encoding="utf-8")
    return fragil, modelo


@con_gcc
def test_crash_y_timeout_quedan_como_casos_con_tags_y_salida(fuentes, tmp_path):
    fragil, modelo = fuentes
    rep = ejecutar_fuzzing(fragil, total_runs=20, timeout_por_run=0.3, seed=3)
    assert rep.crashes and rep.timeouts
    suite = tmp_path / "tests"
    guardados = guardar_casos(rep, suite, modelo)

    entradas = {p.read_text(): p for p in suite.glob("crash_*.in")}
    assert "51\n" in entradas  # el borde exacto del crash, minimizado
    assert "-1\n" in entradas  # el timeout, minimizado
    tags = {e: p.with_suffix(".tags").read_text() for e, p in entradas.items()}
    assert tags["51\n"] == "regresion drake SIGSEGV\n" and tags["-1\n"] == "regresion drake timeout\n"
    assert entradas["51\n"].with_suffix(".out").read_text() == "102\n"
    assert not guardados.descartados

    # Otra corrida no pisa ni duplica: los casos que ya están se cuentan y no se reescriben.
    (suite / "propio.in").write_text("7\n")
    otra = guardar_casos(rep, suite, modelo)
    assert otra.escritos == [] and otra.ya_estaban == len(entradas)


@con_gcc
@pytest.mark.skipif(shutil.which("nostromo") is None, reason="hace falta nostromo")
def test_nostromo_corre_la_suite_el_modelo_pasa_y_el_fragil_no(fuentes, tmp_path):
    fragil, modelo = fuentes
    suite = tmp_path / "tests"
    res = runner.invoke(app, ["fuzz", str(fragil), "-n", "20", "-t", "0.3", "--seed", "3", "--json",
                              "--guardar-casos", str(suite), "--modelo", str(modelo)])
    assert res.exit_code == 1
    binarios = {}
    for nombre, fuente in (("modelo", modelo), ("fragil", fragil)):
        binarios[nombre] = tmp_path / nombre
        subprocess.run(["gcc", str(fuente), "-o", str(binarios[nombre])], check=True)
    correr = ["nostromo", "test", "--etiqueta", "regresion", "--no-hal", "-t", "1", "--json"]
    assert subprocess.run([*correr, str(binarios["modelo"]), str(suite)], capture_output=True).returncode == 0
    assert subprocess.run([*correr, str(binarios["fragil"]), str(suite)], capture_output=True).returncode == 1


@con_gcc
def test_un_caso_en_el_que_el_modelo_tambien_falla_no_entra(fuentes, tmp_path):
    fragil, _ = fuentes
    rep = ejecutar_fuzzing(fragil, total_runs=20, timeout_por_run=0.3, seed=3)
    malo = tmp_path / "malo.c"
    malo.write_text("int main(void) { return 3; }\n", encoding="utf-8")
    guardados = guardar_casos(rep, tmp_path / "tests", malo)
    assert guardados.escritos == []
    assert guardados.descartados and all("código 3" in d for d in guardados.descartados)
