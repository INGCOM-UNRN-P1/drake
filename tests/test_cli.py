"""Tests de integración de la CLI de DRAKE."""

import json
from pathlib import Path
from typer.testing import CliRunner
from drake.cli import app

runner = CliRunner()


def test_cli_version():
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert "DRAKE" in res.stdout


def test_cli_fuzz_json(tmp_path):
    fuente = tmp_path / "prog.c"
    fuente.write_text("int main(void) { return 0; }\n")

    res = runner.invoke(app, ["fuzz", str(fuente), "--runs", "5", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["ok"] is True
    assert data["total_ejecuciones"] == 5


def test_cli_doctor():
    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 0
    assert "Diagnóstico del Entorno DRAKE" in res.stdout

    res_json = runner.invoke(app, ["doctor", "--json"])
    assert res_json.exit_code == 0
    assert '"schema_version": "1.0.0"' in res_json.stdout
    assert '"herramienta": "drake"' in res_json.stdout
    assert '"ok": true' in res_json.stdout

