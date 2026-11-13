import shutil
import zipfile

import pytest

from qa_toolkit.packager import PackagingError, build_skill_zip
from tests.conftest import REAL_SKILL, SKILL_FIXTURE


@pytest.fixture
def skill(tmp_path):
    destination = tmp_path / "origem" / "cenarios-de-teste"
    shutil.copytree(SKILL_FIXTURE, destination)
    return destination


def test_gera_zip_com_a_pasta_da_skill(skill, tmp_path):
    archive = build_skill_zip(skill, tmp_path / "dist")
    assert archive.name == "cenarios-de-teste.zip"
    with zipfile.ZipFile(archive) as bundle:
        assert sorted(bundle.namelist()) == [
            "cenarios-de-teste/SKILL.md",
            "cenarios-de-teste/referencias/guia.md",
        ]
        assert bundle.read("cenarios-de-teste/SKILL.md") == (skill / "SKILL.md").read_bytes()


def test_ignora_arquivos_ocultos_e_cache(skill, tmp_path):
    (skill / ".rascunho.md").write_text("x", encoding="utf-8")
    (skill / "__pycache__").mkdir()
    (skill / "__pycache__" / "a.pyc").write_bytes(b"\0")
    archive = build_skill_zip(skill, tmp_path / "dist")
    with zipfile.ZipFile(archive) as bundle:
        assert not any(".rascunho" in name or "__pycache__" in name for name in bundle.namelist())


def test_build_e_reproduzivel(skill, tmp_path):
    first = build_skill_zip(skill, tmp_path / "a").read_bytes()
    second = build_skill_zip(skill, tmp_path / "b").read_bytes()
    assert first == second


def test_skill_invalida_nao_e_empacotada(skill, tmp_path):
    (skill / "SKILL.md").write_text("sem frontmatter", encoding="utf-8")
    with pytest.raises(PackagingError) as error:
        build_skill_zip(skill, tmp_path / "dist")
    assert error.value.issues
    assert not (tmp_path / "dist").exists()


def test_empacota_a_skill_real(tmp_path):
    archive = build_skill_zip(REAL_SKILL, tmp_path)
    with zipfile.ZipFile(archive) as bundle:
        assert "cenarios-de-teste/SKILL.md" in bundle.namelist()
        assert bundle.testzip() is None
