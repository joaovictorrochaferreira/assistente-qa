import runpy
import shutil
import sys

import pytest

from qa_toolkit import __version__
from qa_toolkit.cli import main
from tests.conftest import INVALID_FEATURES, REAL_SKILL, SKILL_FIXTURE, VALID_FEATURES


def test_validate_skill_ok(capsys):
    assert main(["validate-skill", str(REAL_SKILL)]) == 0
    assert "OK: skill" in capsys.readouterr().out


def test_validate_skill_com_erro(tmp_path, capsys):
    skill = tmp_path / "cenarios-de-teste"
    skill.mkdir()
    (skill / "SKILL.md").write_text("sem frontmatter", encoding="utf-8")
    assert main(["validate-skill", str(skill)]) == 1
    err = capsys.readouterr().err
    assert "ERRO" in err
    assert "Skill inválida" in err


def test_lint_features_ok(capsys):
    assert main(["lint-features", str(VALID_FEATURES)]) == 0
    assert "sem problemas" in capsys.readouterr().out


def test_lint_features_com_erro(capsys):
    assert main(["lint-features", str(INVALID_FEATURES / "id_duplicado.feature")]) == 1
    assert "ID duplicado" in capsys.readouterr().err


def test_lint_features_sem_arquivos(tmp_path, capsys):
    assert main(["lint-features", str(tmp_path)]) == 1
    assert "nenhum arquivo .feature" in capsys.readouterr().err


def test_package_ok(tmp_path, capsys):
    assert main(["package", str(REAL_SKILL), "--output", str(tmp_path)]) == 0
    assert (tmp_path / "cenarios-de-teste.zip").is_file()
    assert "pacote gerado" in capsys.readouterr().out


def test_package_skill_invalida(tmp_path, capsys):
    skill = tmp_path / "cenarios-de-teste"
    shutil.copytree(SKILL_FIXTURE, skill)
    (skill / "SKILL.md").write_text("sem frontmatter", encoding="utf-8")
    assert main(["package", str(skill), "--output", str(tmp_path / "dist")]) == 1
    assert "Empacotamento cancelado" in capsys.readouterr().err


def test_build_site_ok(tmp_path, capsys):
    junit = tmp_path / "junit.xml"
    junit.write_text('<testsuite tests="1" failures="0" errors="0" skipped="0"/>', encoding="utf-8")
    coverage = tmp_path / "coverage.xml"
    coverage.write_text('<coverage line-rate="1"/>', encoding="utf-8")
    args = ["build-site", "--junit", str(junit), "--coverage", str(coverage), "--output", str(tmp_path)]
    assert main(args) == 0
    assert (tmp_path / "index.html").is_file()
    assert "página do relatório" in capsys.readouterr().out


def test_build_site_sem_junit(tmp_path, capsys):
    args = ["build-site", "--junit", str(tmp_path / "x.xml"), "--coverage", str(tmp_path / "y.xml")]
    assert main(args) == 1
    assert "arquivo não encontrado" in capsys.readouterr().err


def test_comando_obrigatorio(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main([])
    assert exit_info.value.code == 2


def test_version(capsys):
    with pytest.raises(SystemExit):
        main(["--version"])
    assert __version__ in capsys.readouterr().out


def test_execucao_como_modulo(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["qa_toolkit", "validate-skill", str(REAL_SKILL)])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("qa_toolkit", run_name="__main__")
    assert exit_info.value.code == 0
