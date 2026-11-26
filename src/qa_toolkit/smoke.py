"""Teste de fumaça: confere se a API implantada responde como esperado.

Roda depois de cada deploy (homologação e produção). Se alguma verificação falhar,
o script de deploy desfaz a implantação. Usa só a biblioteca padrão, para rodar
dentro do próprio container da API.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

# (método, url, corpo JSON ou None) -> (status HTTP, texto da resposta)
Fetch = Callable[[str, str, dict | None], tuple[int, str]]

FEATURE_VALIDA = (
    "CONTEXTO\nDADO que está logado na plataforma\n\n"
    "CT001 - Acesso ao perfil\nDADO que está na tela inicial\n"
    'QUANDO é acionado "Perfil"\nENTÃO é exibida a tela de perfil\n'
)
FEATURE_INVALIDA = "CT001 - Sem contexto\nDADO algo\nQUANDO\n"


@dataclass(frozen=True)
class Check:
    nome: str
    ok: bool
    detalhe: str = ""


def urllib_fetch(method: str, url: str, body: dict | None = None, timeout: float = 5.0) -> tuple[int, str]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as error:
        return 0, str(error)


def _json(text: str) -> dict:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def wait_until_healthy(url: str, fetch: Fetch, attempts: int, interval: float) -> Check:
    last = ""
    for attempt in range(1, attempts + 1):
        status, text = fetch("GET", f"{url}/health", None)
        if status == 200 and _json(text).get("status") == "ok":
            return Check("health", True, f"respondeu na tentativa {attempt}")
        last = f"status {status}"
        if attempt < attempts:
            time.sleep(interval)
    return Check("health", False, f"API não ficou saudável após {attempts} tentativas ({last})")


def check_prometheus(prometheus_url: str, fetch: Fetch, attempts: int, interval: float) -> Check:
    """Confere se o Prometheus está coletando métricas da API (alvo com health 'up')."""
    last = "sem resposta"
    for attempt in range(1, attempts + 1):
        status, text = fetch("GET", f"{prometheus_url}/api/v1/targets", None)
        targets = _json(text).get("data", {}).get("activeTargets", [])
        healths = [
            target.get("health") for target in targets if target.get("labels", {}).get("job") == "qa-toolkit"
        ]
        if status == 200 and "up" in healths:
            return Check("prometheus", True, "alvo qa-toolkit com status up")
        last = f"status {status}, alvos {healths or 'nenhum'}"
        if attempt < attempts:
            time.sleep(interval)
    return Check("prometheus", False, f"Prometheus não está coletando a API ({last})")


def run_smoke(
    url: str,
    prometheus_url: str | None = None,
    fetch: Fetch = urllib_fetch,
    attempts: int = 20,
    interval: float = 3.0,
) -> list[Check]:
    url = url.rstrip("/")
    checks = [wait_until_healthy(url, fetch, attempts, interval)]
    if not checks[0].ok:
        return checks

    status, text = fetch("POST", f"{url}/lint", {"conteudo": FEATURE_VALIDA, "nome": "smoke.feature"})
    body = _json(text)
    checks.append(
        Check("lint de feature válida", status == 200 and body.get("valido") is True, f"status {status}")
    )

    status, text = fetch("POST", f"{url}/lint", {"conteudo": FEATURE_INVALIDA})
    body = _json(text)
    found = body.get("total_problemas", 0)
    checks.append(
        Check(
            "lint de feature inválida",
            status == 200 and body.get("valido") is False and found > 0,
            f"{found} problema(s) apontado(s)",
        )
    )

    status, text = fetch("GET", f"{url}/metrics", None)
    checks.append(
        Check("métricas", status == 200 and "qa_toolkit_http_requests_total" in text, f"status {status}")
    )

    if prometheus_url:
        checks.append(check_prometheus(prometheus_url.rstrip("/"), fetch, attempts, interval))
    return checks
