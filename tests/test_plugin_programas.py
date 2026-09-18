"""Regresión de DRAKE-D0902 (c, d): el plugin fuzzeaba `archivos[0]` sin mirar si era un programa
y reportaba disponibilidad sin comprobar que hubiera compilador."""

import shutil

import pytest

from drake.ripley_plugin import DrakePlugin, _programas

necesita_gcc = pytest.mark.skipif(not shutil.which("gcc"), reason="requiere gcc")

PROGRAMA = "#include <stdio.h>\nint main(void) { return 0; }\n"
MODULO = "int suma(int a, int b) { return a + b; }\n"


def test_solo_se_toman_los_archivos_que_definen_main(tmp_path):
    (tmp_path / "a_modulo.c").write_text(MODULO, encoding="utf-8")
    (tmp_path / "main.c").write_text(PROGRAMA, encoding="utf-8")
    assert [p.name for p in _programas(tmp_path, {})] == ["main.c"]


def test_el_primer_archivo_del_glob_ya_no_decide(tmp_path):
    """Con un módulo que ordena antes que el programa, antes se fuzzeaba el módulo."""
    (tmp_path / "a_modulo.c").write_text(MODULO, encoding="utf-8")
    (tmp_path / "z_main.c").write_text(PROGRAMA, encoding="utf-8")
    assert [p.name for p in _programas(tmp_path, {})] == ["z_main.c"]


def test_un_archivo_como_workspace_se_acepta(tmp_path):
    f = tmp_path / "solo.c"
    f.write_text(PROGRAMA, encoding="utf-8")
    assert _programas(f, {}) == [f]


def test_c_files_del_manifiesto_tiene_prioridad(tmp_path):
    (tmp_path / "main.c").write_text(PROGRAMA, encoding="utf-8")
    otro = tmp_path / "otro.c"
    otro.write_text(PROGRAMA, encoding="utf-8")
    assert _programas(tmp_path, {"c_files": [str(otro)]}) == [otro]


def test_sin_gcc_el_plugin_no_esta_disponible(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    assert DrakePlugin().is_available() is False


@necesita_gcc
def test_se_fuzzean_todos_los_programas(tmp_path):
    (tmp_path / "uno.c").write_text(PROGRAMA, encoding="utf-8")
    (tmp_path / "dos.c").write_text(PROGRAMA, encoding="utf-8")
    res = DrakePlugin().execute(tmp_path, {"runs": 3})
    assert res["ok"] is True
    assert res["total_runs"] == 6
