import shutil
from pathlib import Path

import pytest

from qa_toolkit.skill_validator import slugify, validate_skill
from tests.conftest import REAL_SKILL, SKILL_FIXTURE


@pytest.fixture
def skill(tmp_path: Path) -> Path:
    """Cópia editável da skill de fixture, dentro de uma pasta com o nome correto."""
    destination = tmp_path / "cenarios-de-teste"
    shutil.copytree(SKILL_FIXTURE, destination)
    return destination


def _edit(skill: Path, old: str, new: str) -> None:
    file = skill / "SKILL.md"
    text = file.read_text(encoding="utf-8")
    assert old in text, f"trecho não encontrado na fixture: {old!r}"
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


def _messages(skill: Path) -> list[str]:
    return [issue.message for issue in validate_skill(skill)]


def test_skill_real_do_repositorio_e_valida():
    assert validate_skill(REAL_SKILL) == []


def test_fixture_valida_nao_tem_problemas(skill):
    assert validate_skill(skill) == []


def test_aceita_caminho_do_proprio_skill_md(skill):
    assert validate_skill(skill / "SKILL.md") == []


def test_pasta_sem_skill_md(tmp_path):
    assert _messages(tmp_path) == ["arquivo SKILL.md não encontrado"]


def test_sem_frontmatter(skill):
    file = skill / "SKILL.md"
    text = file.read_text(encoding="utf-8")
    file.write_text(text.split("---", 2)[2], encoding="utf-8")
    assert any("frontmatter ausente" in message for message in _messages(skill))


def test_frontmatter_sem_fechamento(skill):
    (skill / "SKILL.md").write_text("---\nname: cenarios-de-teste\n", encoding="utf-8")
    assert "frontmatter sem o --- de fechamento" in _messages(skill)


def test_frontmatter_com_yaml_invalido(skill):
    _edit(skill, "name: cenarios-de-teste", "name: [sem fechar")
    assert any("YAML inválido" in message for message in _messages(skill))


def test_frontmatter_que_nao_e_mapa(skill):
    _edit(skill, "name: cenarios-de-teste\ndescription:", "- item\n- outro\n#")
    assert "frontmatter deve ser um mapa chave: valor" in _messages(skill)


def test_name_ausente(skill):
    _edit(skill, "name: cenarios-de-teste\n", "")
    assert "campo 'name' ausente ou vazio no frontmatter" in _messages(skill)


@pytest.mark.parametrize("name", ["Cenarios-De-Teste", "cenarios_de_teste", "cenarios--teste"])
def test_name_fora_do_padrao(skill, name):
    _edit(skill, "name: cenarios-de-teste", f"name: {name}")
    assert any("só minúsculas, números e hífens" in message for message in _messages(skill))


def test_name_muito_longo(skill):
    _edit(skill, "name: cenarios-de-teste", "name: " + "a" * 65)
    assert any("passa de 64 caracteres" in message for message in _messages(skill))


def test_name_diferente_da_pasta(skill):
    _edit(skill, "name: cenarios-de-teste", "name: outra-skill")
    assert any("difere do nome da pasta" in message for message in _messages(skill))


def test_description_ausente(skill):
    _edit(skill, "description: Skill mínima e válida usada como fixture nos testes do validador.\n", "")
    assert "campo 'description' ausente ou vazio no frontmatter" in _messages(skill)


def test_description_muito_longa(skill):
    _edit(skill, "description: Skill", "description: " + "x" * 1100)
    assert any("'description' passa de 1024" in message for message in _messages(skill))


def test_etapa_ausente(skill):
    _edit(skill, "### Etapa 6: Validação\n", "")
    assert "Etapa obrigatória ausente: '### Etapa 6: ...'" in _messages(skill)


def test_etapa_repetida(skill):
    _edit(skill, "### Etapa 7: Execução assistida", "### Etapa 7: Execução assistida\n### Etapa 7: De novo")
    assert any("Etapa 7 aparece mais de uma vez" in message for message in _messages(skill))


def test_etapa_fora_de_ordem(skill):
    _edit(
        skill, "### Etapa 2: Background\n### Etapa 3: Plano de testes", "### Etapa 3: Plano\n### Etapa 2: Bg"
    )
    assert any("Etapa 2 está fora de ordem" in message for message in _messages(skill))


def test_titulo_dentro_de_bloco_de_codigo_e_ignorado(skill):
    # A fixture tem "### Etapa 9" e um link quebrado dentro de um bloco ```text```.
    assert validate_skill(skill) == []


def test_secao_obrigatoria_ausente(skill):
    _edit(skill, "## Fontes de informação", "## Entradas")
    assert "seção obrigatória ausente: '## Fontes de informação'" in _messages(skill)


def test_ancora_interna_inexistente(skill):
    _edit(skill, "(#formato-de-saída-obrigatório)", "(#secao-que-nao-existe)")
    assert any("âncora interna inexistente" in message for message in _messages(skill))


def test_link_para_arquivo_inexistente(skill):
    _edit(skill, "referencias/guia.md#técnicas", "referencias/nao-existe.md")
    assert any("link para arquivo inexistente" in message for message in _messages(skill))


def test_ancora_inexistente_no_arquivo_de_destino(skill):
    _edit(skill, "guia.md#técnicas", "guia.md#nao-existe")
    assert any("âncora inexistente no arquivo de destino" in message for message in _messages(skill))


def test_link_para_fora_da_skill(skill):
    _edit(skill, "referencias/guia.md#técnicas", "../README.md")
    assert any("fora da pasta da skill" in message for message in _messages(skill))


def test_links_externos_e_codigo_inline_sao_ignorados(skill):
    _edit(
        skill,
        "Tarefa, diff e regras de negócio.",
        "Veja [o site](https://exemplo.com) e `[exemplo](nao-existe.md)`.",
    )
    assert validate_skill(skill) == []


def test_problema_informa_arquivo_e_linha(skill):
    _edit(skill, "(#formato-de-saída-obrigatório)", "(#nao-existe)")
    issue = validate_skill(skill)[0]
    assert issue.line == 8
    assert str(issue).endswith("SKILL.md:8: âncora interna inexistente: #nao-existe")


@pytest.mark.parametrize(
    ("title", "slug"),
    [
        ("Formato de saída (obrigatório)", "formato-de-saída-obrigatório"),
        ("Etapa 6: Validação pelo conselho de QA", "etapa-6-validação-pelo-conselho-de-qa"),
        ("Quando usar `esta` skill", "quando-usar-esta-skill"),
    ],
)
def test_slugify_segue_o_padrao_do_github(title, slug):
    assert slugify(title) == slug
