"""API HTTP do qa-toolkit.

Rotas:
    GET  /                informações do serviço
    GET  /health          verificação de saúde (usada pelo Docker e pelo deploy)
    POST /lint            confere o texto de um arquivo .feature
    POST /validate-skill  valida o texto de um SKILL.md
    GET  /metrics         métricas no formato do Prometheus

Configuração por variáveis de ambiente (veja ``Settings``). Os logs saem em JSON,
uma linha por evento, para serem lidos por ferramentas de agregação de logs.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, Field

from qa_toolkit import __version__
from qa_toolkit.feature_linter import lint_text
from qa_toolkit.issues import Issue
from qa_toolkit.skill_validator import validate_skill_text

LOGGER_NAME = "qa_toolkit.api"


@dataclass(frozen=True)
class Settings:
    """Configuração da API, lida do ambiente para o mesmo container servir qualquer ambiente."""

    environment: str = "local"
    log_level: str = "INFO"
    max_body_bytes: int = 256 * 1024

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            environment=os.environ.get("QA_TOOLKIT_AMBIENTE", cls.environment),
            log_level=os.environ.get("QA_TOOLKIT_LOG_LEVEL", cls.log_level).upper(),
            max_body_bytes=int(os.environ.get("QA_TOOLKIT_MAX_BYTES", cls.max_body_bytes)),
        )


class JsonFormatter(logging.Formatter):
    """Formata cada registro de log como um objeto JSON em uma linha."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "nivel": record.levelname,
            "logger": record.name,
            "mensagem": record.getMessage(),
        }
        payload.update(getattr(record, "campos", {}))
        return json.dumps(payload, ensure_ascii=False)


class _StdoutHandler(logging.StreamHandler):
    """Escreve sempre no sys.stdout atual (o Docker coleta os logs da saída padrão)."""

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, _value):
        pass


def configure_logging(level: str) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    if not logger.handlers:
        handler = _StdoutHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    return logger


class Metrics:
    """Métricas expostas em /metrics. Cada app tem seu próprio registro."""

    def __init__(self, settings: Settings):
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "qa_toolkit_http_requests",
            "Requisições HTTP recebidas",
            ["metodo", "rota", "status"],
            registry=self.registry,
        )
        self.latency = Histogram(
            "qa_toolkit_http_request_duration_seconds",
            "Tempo de resposta das requisições HTTP",
            ["rota"],
            registry=self.registry,
        )
        self.validations = Counter(
            "qa_toolkit_validacoes",
            "Validações executadas, por tipo e resultado",
            ["tipo", "resultado"],
            registry=self.registry,
        )
        self.problems = Counter(
            "qa_toolkit_problemas_encontrados",
            "Problemas encontrados nas validações",
            ["tipo"],
            registry=self.registry,
        )
        info = Gauge(
            "qa_toolkit_build_info",
            "Versão e ambiente em execução",
            ["versao", "ambiente"],
            registry=self.registry,
        )
        info.labels(versao=__version__, ambiente=settings.environment).set(1)


class LintRequest(BaseModel):
    conteudo: str = Field(description="Texto completo do arquivo .feature")
    nome: str = Field(default="entrada.feature", description="Nome do arquivo, usado nas mensagens")


class SkillRequest(BaseModel):
    conteudo: str = Field(description="Texto completo do SKILL.md")


def _result(issues: list[Issue]) -> dict:
    return {
        "valido": not issues,
        "total_problemas": len(issues),
        "problemas": [{"linha": issue.line, "mensagem": issue.message} for issue in issues],
    }


def _too_large(settings: Settings) -> JSONResponse:
    return JSONResponse(
        status_code=413,
        content={"erro": f"conteúdo maior que o limite de {settings.max_body_bytes} bytes"},
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    logger = configure_logging(settings.log_level)
    metrics = Metrics(settings)

    app = FastAPI(
        title="qa-toolkit",
        version=__version__,
        description="Valida a skill cenarios-de-teste e arquivos .feature no formato da skill.",
    )
    app.state.settings = settings
    app.state.metrics = metrics

    @app.middleware("http")
    async def observability(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        started = time.perf_counter()

        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > settings.max_body_bytes:
            response = _too_large(settings)
        else:
            response = await call_next(request)

        route = request.scope.get("route")
        route_path = getattr(route, "path", "desconhecida")
        elapsed = time.perf_counter() - started
        metrics.requests.labels(request.method, route_path, str(response.status_code)).inc()
        metrics.latency.labels(route_path).observe(elapsed)
        response.headers["X-Request-ID"] = request_id

        level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(
            level,
            "requisição atendida",
            extra={
                "campos": {
                    "request_id": request_id,
                    "metodo": request.method,
                    "rota": route_path,
                    "status": response.status_code,
                    "duracao_ms": round(elapsed * 1000, 2),
                    "ambiente": settings.environment,
                }
            },
        )
        return response

    def record(kind: str, issues: list[Issue]) -> None:
        metrics.validations.labels(kind, "reprovado" if issues else "aprovado").inc()
        metrics.problems.labels(kind).inc(len(issues))

    @app.get("/")
    def info() -> dict:
        return {
            "servico": "qa-toolkit",
            "versao": __version__,
            "ambiente": settings.environment,
            "rotas": ["/health", "/lint", "/validate-skill", "/metrics", "/docs"],
        }

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "versao": __version__, "ambiente": settings.environment}

    @app.post("/lint")
    def lint(body: LintRequest):
        if len(body.conteudo.encode("utf-8")) > settings.max_body_bytes:
            return _too_large(settings)
        issues = lint_text(body.conteudo, Path(Path(body.nome).name or "entrada.feature"))
        record("feature", issues)
        return _result(issues)

    @app.post("/validate-skill")
    def validate_skill(body: SkillRequest):
        if len(body.conteudo.encode("utf-8")) > settings.max_body_bytes:
            return _too_large(settings)
        issues = validate_skill_text(body.conteudo, Path("SKILL.md"), standalone=True)
        record("skill", issues)
        return _result(issues)

    @app.get("/metrics")
    def prometheus_metrics() -> Response:
        return Response(generate_latest(metrics.registry), media_type=CONTENT_TYPE_LATEST)

    logger.info(
        "api iniciada",
        extra={"campos": {"versao": __version__, "ambiente": settings.environment}},
    )
    return app
