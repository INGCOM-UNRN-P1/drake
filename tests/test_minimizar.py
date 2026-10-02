"""Entrada mínima que hace fallar al programa y casos de nostromo (QoL #264)."""

import shutil

import pytest
from typer.testing import CliRunner

from drake.cli import app
from drake.core.fuzzer import ejecutar_fuzzing

runner = CliRunner()
con_gcc = pytest.mark.skipif(shutil.which("gcc") is None, reason="hace falta gcc")

# Rompe con una línea de más de 15 caracteres (strcpy a un buffer de 16).
FRAGIL = """#include <stdio.h>
#include <string.h>
int main(void)
{
    char linea[8192];
    char corto[16];
    if (fgets(linea, sizeof(linea), stdin) == NULL)
    {
        return 0;
    }
    if (strlen(linea) > 15)
    {
        int *p = NULL;
        return *p;
    }
    strcpy(corto, linea);
    printf("%s", corto);
    return 0;
}
"""
MODELO = """#include <stdio.h>
#include <string.h>
int main(void)
{
    char linea[8192];
    if (fgets(linea, sizeof(linea), stdin) != NULL)
    {
        printf("%zu\\n", strlen(linea));
    }
    return 0;
}
"""


@con_gcc
def test_la_entrada_minima_es_chica(tmp_path):
    fuente = tmp_path / "fragil.c"
    fuente.write_text(FRAGIL, encoding="utf-8")
    rep = ejecutar_fuzzing(fuente, total_runs=10, seed=1)
    crash = next(c for c in rep.crashes if c.senal_error == "SIGSEGV")
    assert len(crash.payload_input) >= 1024 and 16 <= len(crash.payload_minimo) <= 17


@con_gcc
def test_guardar_casos_con_modelo(tmp_path):
    fuente = tmp_path / "fragil.c"
    fuente.write_text(FRAGIL, encoding="utf-8")
    modelo = tmp_path / "modelo.c"
    modelo.write_text(MODELO, encoding="utf-8")
    destino = tmp_path / "casos"
    res = runner.invoke(app, ["fuzz", str(fuente), "-n", "10", "--seed", "1", "--json",
                              "--guardar-casos", str(destino), "--modelo", str(modelo)])
    assert res.exit_code == 1
    entrada = (destino / "crash_01.in").read_text(encoding="utf-8")
    assert len(entrada) <= 17
    assert (destino / "crash_01.out").read_text(encoding="utf-8") == f"{len(entrada)}\n"
