import json
import logging

import pytest
from fastapi.testclient import TestClient

from qa_toolkit import __version__
from qa_toolkit.api import LOGGER_NAME, JsonFormatter, Settings, create_app
from tests.conftest import REAL_SKILL, VALID_FEATURES

FEATURE_VALIDA = (VALID_FEATURES / "login.feature").read_text(encoding="utf-8")
SKILL_REAL = (REAL_SKILL / "SKILL.md").read_text(encoding="utf-8")


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(Settings(environment="teste", max_body_bytes=4096)))


def test_info(client):
    body = client.get("/").json()
    assert body["servico"] == "qa-toolkit"
    assert body["ambiente"] == "teste"
    assert "/lint" in body["rotas"]


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "versao": __version__, "ambiente": "teste"}


def test_lint_feature_valida(client):
    body = client.post("/lint", json={"conteudo": FEATURE_VALIDA, "nome": "login.feature"}).json()
    assert body == {"valido": True, "total_problemas": 0, "problemas": []}


def test_lint_feature_invalida_aponta_linha_e_motivo(client):
    body = client.post("/lint", json={"conteudo": "CT001 - X\nDADO a\nQUANDO\n"}).json()
    assert body["valido"] is False
    assert {"linha": 3, "mensagem": "passo vazio: 'QUANDO' sem descrição"} in body["problemas"]


def test_lint_sem_campo_conteudo_retorna_422(client):
    assert client.post("/lint", json={}).status_code == 422


def test_validate_skill_real_e_valida(client):
    big = TestClient(create_app(Settings(max_body_bytes=1024 * 1024)))
    body = big.post("/validate-skill", json={"conteudo": SKILL_REAL}).json()
    assert body["valido"] is True


def test_validate_skill_invalida(client):
    body = client.post("/validate-skill", json={"conteudo": "sem frontmatter"}).json()
    assert body["valido"] is False
    assert body["total_problemas"] > 0


@pytest.mark.parametrize("rota", ["/lint", "/validate-skill"])
def test_conteudo_acima_do_limite_retorna_413(client, rota):
    response = client.post(rota, json={"conteudo": "x" * 5000})
    assert response.status_code == 413
    assert "limite de 4096 bytes" in response.json()["erro"]


@pytest.mark.parametrize("rota", ["/lint", "/validate-skill"])
def test_limite_vale_mesmo_sem_content_length(client, rota):
    # Corpo enviado em partes (chunked) não tem Content-Length: quem barra é a própria rota.
    body = json.dumps({"conteudo": "é" * 3000}, ensure_ascii=False).encode("utf-8")
    response = client.post(rota, content=iter([body]), headers={"content-type": "application/json"})
    assert response.status_code == 413


def test_metricas_contam_requisicoes_e_validacoes(client):
    client.post("/lint", json={"conteudo": FEATURE_VALIDA})
    client.post("/lint", json={"conteudo": "CT001 - X\n"})
    text = client.get("/metrics").text
    assert 'qa_toolkit_http_requests_total{metodo="POST",rota="/lint",status="200"} 2.0' in text
    assert 'qa_toolkit_validacoes_total{resultado="aprovado",tipo="feature"} 1.0' in text
    assert 'qa_toolkit_validacoes_total{resultado="reprovado",tipo="feature"} 1.0' in text
    assert f'qa_toolkit_build_info{{ambiente="teste",versao="{__version__}"}} 1.0' in text
    assert "qa_toolkit_http_request_duration_seconds_bucket" in text


def test_rota_inexistente_nao_explode_as_metricas(client):
    assert client.get("/nao-existe").status_code == 404
    assert 'rota="desconhecida",status="404"' in client.get("/metrics").text


def test_request_id_e_devolvido(client):
    response = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert response.headers["X-Request-ID"] == "abc123"
    assert len(client.get("/health").headers["X-Request-ID"]) == 32


def test_log_em_json_por_requisicao(client, capsys):
    client.get("/health", headers={"X-Request-ID": "log-1"})
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    entry = next(line for line in lines if line.get("request_id") == "log-1")
    assert entry["mensagem"] == "requisição atendida"
    assert entry["rota"] == "/health"
    assert entry["status"] == 200
    assert entry["nivel"] == "INFO"
    assert entry["ambiente"] == "teste"


def test_erro_e_logado_como_warning(client, capsys):
    client.post("/lint", json={})
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert any(line.get("status") == 422 and line["nivel"] == "WARNING" for line in lines)


def test_settings_lidas_do_ambiente(monkeypatch):
    monkeypatch.setenv("QA_TOOLKIT_AMBIENTE", "producao")
    monkeypatch.setenv("QA_TOOLKIT_LOG_LEVEL", "debug")
    monkeypatch.setenv("QA_TOOLKIT_MAX_BYTES", "1234")
    assert Settings.from_env() == Settings(environment="producao", log_level="DEBUG", max_body_bytes=1234)


def test_create_app_sem_settings_usa_o_ambiente(monkeypatch):
    monkeypatch.setenv("QA_TOOLKIT_AMBIENTE", "homologacao")
    assert TestClient(create_app()).get("/health").json()["ambiente"] == "homologacao"


def test_json_formatter():
    record = logging.LogRecord(LOGGER_NAME, logging.INFO, __file__, 1, "olá", None, None)
    record.campos = {"chave": "valor"}
    payload = json.loads(JsonFormatter().format(record))
    assert payload["mensagem"] == "olá"
    assert payload["chave"] == "valor"
    assert payload["timestamp"].endswith("+00:00")
