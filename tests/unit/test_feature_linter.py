from pathlib import Path

import pytest

from qa_toolkit.feature_linter import collect_feature_files, lint_file, lint_paths
from tests.conftest import INVALID_FEATURES, ROOT, VALID_FEATURES

# Cada fixture inválida tem um defeito principal: (arquivo, linha esperada, trecho da mensagem).
INVALID_CASES = [
    ("sem_contexto.feature", 1, "arquivo sem bloco CONTEXTO"),
    ("id_duplicado.feature", 9, "ID duplicado: CT001 já usado na linha 4"),
    ("fora_de_sequencia.feature", 9, "ID fora de sequência: esperado CT002, achado CT003"),
    ("passo_vazio.feature", 6, "passo vazio: 'QUANDO' sem descrição"),
    ("cenario_sem_passos.feature", 4, "CT001 sem passos"),
    ("sem_entao.feature", 4, "CT001 sem passo ENTÃO"),
    ("ordem_errada.feature", 7, "QUANDO após ENTÃO"),
    ("palavra_chave_minuscula.feature", 5, "palavra-chave 'Dado' fora do padrão: use 'DADO'"),
    ("usa_and.feature", 6, "palavra-chave 'AND' fora do padrão: use 'E'"),
    ("indentado.feature", 5, "linha com indentação"),
    ("linha_em_branco_entre_passos.feature", 7, "linha em branco entre os passos de CT001"),
    ("cabecalho_gherkin.feature", 4, "cabeçalho fora do formato"),
    ("contexto_com_acao.feature", 3, "CONTEXTO só deve ter passos de estado"),
]


@pytest.mark.parametrize("feature", sorted(VALID_FEATURES.glob("*.feature")), ids=lambda p: p.name)
def test_fixtures_validas_nao_tem_problemas(feature):
    assert lint_file(feature) == []


def test_features_de_exemplo_do_repositorio_sao_validas():
    files, issues = lint_paths([ROOT / "features"])
    assert files, "a pasta features/ deveria ter arquivos .feature"
    assert issues == []


@pytest.mark.parametrize(("name", "line", "message"), INVALID_CASES, ids=[c[0] for c in INVALID_CASES])
def test_fixtures_invalidas_apontam_o_defeito(name, line, message):
    issues = lint_file(INVALID_FEATURES / name)
    assert any(issue.line == line and message in issue.message for issue in issues), "\n".join(
        str(issue) for issue in issues
    )


def test_toda_fixture_invalida_esta_coberta_por_um_caso():
    files = {path.name for path in INVALID_FEATURES.glob("*.feature")}
    assert files == {case[0] for case in INVALID_CASES}


def _write(tmp_path: Path, content: str) -> Path:
    file = tmp_path / "caso.feature"
    file.write_text(content, encoding="utf-8")
    return file


def test_contexto_depois_dos_cenarios(tmp_path):
    file = _write(
        tmp_path,
        "CT001 - Cenário\nDADO a\nQUANDO b\nENTÃO c\n\nCONTEXTO\nDADO que está logado\n",
    )
    messages = [issue.message for issue in lint_file(file)]
    assert "o CONTEXTO deve vir antes do primeiro cenário" in messages


def test_contexto_sem_passos_e_sem_cenarios(tmp_path):
    messages = [issue.message for issue in lint_file(_write(tmp_path, "CONTEXTO\n"))]
    assert "CONTEXTO sem passos" in messages
    assert "arquivo sem cenários (CT001 - ...)" in messages


def test_contexto_deve_comecar_com_dado(tmp_path):
    file = _write(tmp_path, "CONTEXTO\nE algo\n\nCT001 - X\nDADO a\nQUANDO b\nENTÃO c\n")
    assert any("CONTEXTO deve começar com DADO" in issue.message for issue in lint_file(file))


def test_cenario_nao_pode_comecar_com_e(tmp_path):
    file = _write(tmp_path, "CONTEXTO\nDADO a\n\nCT001 - X\nE a\nDADO a\nQUANDO b\nENTÃO c\n")
    assert any("CT001 não pode começar com E" in issue.message for issue in lint_file(file))


def test_passo_antes_de_qualquer_bloco(tmp_path):
    file = _write(tmp_path, "DADO solto\nCONTEXTO\nDADO a\n\nCT001 - X\nDADO a\nQUANDO b\nENTÃO c\n")
    assert any("passo fora de um bloco" in issue.message for issue in lint_file(file))


def test_titulo_de_cenario_mal_formatado(tmp_path):
    file = _write(tmp_path, "CONTEXTO\nDADO a\n\nCT1 Sem hífen\nDADO a\n")
    assert any("título de cenário fora do formato" in issue.message for issue in lint_file(file))


def test_linha_nao_reconhecida(tmp_path):
    file = _write(tmp_path, "CONTEXTO\nDADO a\nTexto solto\n\nCT001 - X\nDADO a\nQUANDO b\nENTÃO c\n")
    assert any("linha não reconhecida" in issue.message for issue in lint_file(file))


def test_comentarios_sao_ignorados(tmp_path):
    file = _write(tmp_path, "# comentário\nCONTEXTO\nDADO a\n# outro\nCT001 - X\nDADO a\nQUANDO b\nENTÃO c\n")
    assert lint_file(file) == []


def test_arquivo_que_nao_e_utf8(tmp_path):
    file = tmp_path / "latin1.feature"
    file.write_bytes("CONTEXTO\nDADO não\n".encode("latin-1"))
    assert [issue.message for issue in lint_file(file)] == ["arquivo não está em UTF-8"]


def test_problemas_saem_ordenados_por_linha():
    issues = lint_file(INVALID_FEATURES / "cenario_sem_passos.feature")
    lines = [issue.line or 0 for issue in issues]
    assert lines == sorted(lines)


def test_collect_expande_pastas_e_mantem_arquivos(tmp_path):
    single = _write(tmp_path, "CONTEXTO\n")
    files = collect_feature_files([VALID_FEATURES, single])
    assert files[-1] == single
    assert all(path.suffix == ".feature" for path in files)


def test_lint_paths_com_arquivo_inexistente(tmp_path):
    _files, issues = lint_paths([tmp_path / "nao-existe.feature"])
    assert [issue.message for issue in issues] == ["arquivo não encontrado"]
