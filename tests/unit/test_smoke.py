import json
import urllib.error

import pytest
from fastapi.testclient import TestClient

from qa_toolkit import smoke
from qa_toolkit.api import Settings, create_app
from qa_toolkit.smoke import run_smoke, urllib_fetch

URL = "http://api"
PROMETHEUS = "http://prometheus"


def _prometheus_targets(health: str) -> str:
    return json.dumps({"data": {"activeTargets": [{"labels": {"job": "qa-toolkit"}, "health": health}]}})


def make_fetch(prometheus_health: str = "up", api_down_times: int = 0):
    """Simula a rede: a API é atendida por um TestClient e o Prometheus por uma resposta fixa."""
    client = TestClient(create_app(Settings(environment="teste")))
    state = {"down": api_down_times}

    def fetch(method, url, body):
        if url.startswith(PROMETHEUS):
            return 200, _prometheus_targets(prometheus_health)
        if state["down"] > 0:
            state["down"] -= 1
            return 0, "connection refused"
        path = url.removeprefix(URL)
        response = client.request(method, path, json=body)
        return response.status_code, response.text

    return fetch


def test_smoke_aprovado_com_prometheus():
    checks = run_smoke(URL, PROMETHEUS, fetch=make_fetch(), attempts=2, interval=0)
    assert [check.nome for check in checks] == [
        "health",
        "lint de feature válida",
        "lint de feature inválida",
        "métricas",
        "prometheus",
    ]
    assert all(check.ok for check in checks)


def test_smoke_espera_a_api_subir():
    checks = run_smoke(URL, fetch=make_fetch(api_down_times=2), attempts=5, interval=0)
    assert checks[0].ok
    assert checks[0].detalhe == "respondeu na tentativa 3"


def test_smoke_para_se_a_api_nunca_sobe():
    checks = run_smoke(URL, fetch=make_fetch(api_down_times=99), attempts=3, interval=0)
    assert len(checks) == 1
    assert not checks[0].ok
    assert "após 3 tentativas" in checks[0].detalhe


def test_smoke_reprova_se_prometheus_nao_coleta():
    checks = run_smoke(URL, PROMETHEUS, fetch=make_fetch(prometheus_health="down"), attempts=2, interval=0)
    assert not checks[-1].ok
    assert "alvos ['down']" in checks[-1].detalhe


def test_smoke_reprova_resposta_inesperada():
    def fetch(method, url, body):
        if url.endswith("/health"):
            return 200, '{"status": "ok"}'
        return 500, "erro interno"

    checks = run_smoke(URL, fetch=fetch, attempts=1, interval=0)
    assert checks[0].ok
    assert not any(check.ok for check in checks[1:])


def test_json_invalido_ou_nao_objeto_vira_dicionario_vazio():
    assert smoke._json("não é json") == {}
    assert smoke._json("[1, 2]") == {}


class _FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b'{"ok": true}'


def test_urllib_fetch_envia_json(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        return _FakeResponse()

    monkeypatch.setattr(smoke.urllib.request, "urlopen", fake_urlopen)
    assert urllib_fetch("POST", "http://x/lint", {"a": 1}) == (200, '{"ok": true}')
    assert captured["request"].get_header("Content-type") == "application/json"
    assert captured["request"].data == b'{"a": 1}'


def test_urllib_fetch_erro_http(monkeypatch):
    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 503, "indisponível", None, _Body(b"fora"))

    monkeypatch.setattr(smoke.urllib.request, "urlopen", fake_urlopen)
    assert urllib_fetch("GET", "http://x/health") == (503, "fora")


@pytest.mark.parametrize("error", [urllib.error.URLError("recusado"), ConnectionResetError("reset")])
def test_urllib_fetch_sem_conexao(monkeypatch, error):
    def fake_urlopen(request, timeout):
        raise error

    monkeypatch.setattr(smoke.urllib.request, "urlopen", fake_urlopen)
    status, _text = urllib_fetch("GET", "http://x/health")
    assert status == 0


class _Body:
    def __init__(self, data):
        self.data = data

    def read(self):
        return self.data

    def close(self):
        pass
