"""Tests adicionales para maximizar la cobertura en DRAKE."""

import json
from pathlib import Path
from typer.testing import CliRunner
import drake.cli
from drake.cli import app
from drake.core.fuzzer import ejecutar_fuzzing, generar_payload_mutado
from drake.ripley_plugin import DrakePlugin

runner = CliRunner()


def test_plugin_execution(tmp_path):
    p = DrakePlugin()
    assert p.is_available() is True

    # Empty workspace
    res_empty = p.execute(tmp_path, {})
    assert res_empty["ok"] is True

    # Workspace with program
    f = tmp_path / "main.c"
    f.write_text("int main(void) { return 0; }\n")
    res_ok = p.execute(tmp_path, {})
    assert res_ok["ok"] is True
    assert res_ok["total_runs"] > 0


def test_cli_fuzz_rich_success_and_fail(tmp_path):
    # Success
    f_ok = tmp_path / "ok.c"
    f_ok.write_text("int main(void) { return 0; }\n")
    res_ok = runner.invoke(app, ["fuzz", str(f_ok), "--runs", "5"])
    assert res_ok.exit_code == 0
    assert "Fuzzing completado exitosamente" in res_ok.stdout

    # Crash
    f_crash = tmp_path / "crash.c"
    f_crash.write_text("""
    #include <stdio.h>
    int main(void) {
        int x;
        if (scanf("%d", &x) == 1 && x == 0) {
            int *p = NULL;
            *p = 1;
        }
        return 0;
    }
    """)
    res_c = runner.invoke(app, ["fuzz", str(f_crash), "--runs", "10"])
    assert res_c.exit_code == 1
    assert "Crashes Detectados" in res_c.stdout


def test_cli_file_not_found():
    res = runner.invoke(app, ["fuzz", "/no/existe.c"])
    assert res.exit_code == 2


def test_fuzzer_mutations():
    # Test random mutations
    p1 = generar_payload_mutado(25)
    p2 = generar_payload_mutado(26)
    assert len(p1) > 0
    assert len(p2) > 0


def test_cli_main_block(monkeypatch):
    monkeypatch.setattr("sys.argv", ["drake", "--version"])
    try:
        drake.cli.main()
    except SystemExit as e:
        assert e.code == 0
