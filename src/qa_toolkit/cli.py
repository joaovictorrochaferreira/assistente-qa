"""Linha de comando do qa-toolkit.

Uso:
    qa-toolkit validate-skill skill/cenarios-de-teste
    qa-toolkit lint-features features
    qa-toolkit package skill/cenarios-de-teste --output dist
    qa-toolkit build-site --junit reports/junit.xml --coverage reports/coverage.xml --output site
    qa-toolkit serve --host 0.0.0.0 --port 8000
    qa-toolkit smoke-test --url http://localhost:8000 --prometheus-url http://localhost:9090
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from qa_toolkit import __version__
from qa_toolkit.feature_linter import lint_paths
from qa_toolkit.issues import Issue
from qa_toolkit.packager import PackagingError, build_skill_zip
from qa_toolkit.site_builder import build_site
from qa_toolkit.skill_validator import validate_skill


def _report(issues: list[Issue]) -> None:
    for issue in issues:
        print(f"ERRO {issue}", file=sys.stderr)


def _cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn

        from qa_toolkit.api import create_app
    except ImportError:
        print("ERRO dependências da API ausentes: pip install 'qa-toolkit[api]'", file=sys.stderr)
        return 1
    # access_log desligado: a própria API registra cada requisição em JSON.
    uvicorn.run(create_app(), host=args.host, port=args.port, access_log=False, log_level="warning")
    return 0


def _cmd_smoke_test(args: argparse.Namespace) -> int:
    from qa_toolkit.smoke import run_smoke

    checks = run_smoke(args.url, args.prometheus_url, attempts=args.tentativas, interval=args.intervalo)
    for check in checks:
        print(f"{'OK  ' if check.ok else 'FALHA'} {check.nome}: {check.detalhe}")
    if all(check.ok for check in checks):
        print("Teste de fumaça aprovado.")
        return 0
    print("Teste de fumaça reprovado.", file=sys.stderr)
    return 1


def _cmd_validate_skill(args: argparse.Namespace) -> int:
    issues = validate_skill(args.path)
    if issues:
        _report(issues)
        print(f"Skill inválida: {len(issues)} problema(s).", file=sys.stderr)
        return 1
    print(f"OK: skill {args.path} válida.")
    return 0


def _cmd_lint_features(args: argparse.Namespace) -> int:
    files, issues = lint_paths(args.paths)
    if not files:
        print("ERRO nenhum arquivo .feature encontrado.", file=sys.stderr)
        return 1
    if issues:
        _report(issues)
        print(f"{len(issues)} problema(s) em {len(files)} arquivo(s).", file=sys.stderr)
        return 1
    print(f"OK: {len(files)} arquivo(s) .feature sem problemas.")
    return 0


def _cmd_package(args: argparse.Namespace) -> int:
    try:
        archive = build_skill_zip(args.path, args.output)
    except PackagingError as error:
        _report(error.issues)
        print(f"Empacotamento cancelado: {error}.", file=sys.stderr)
        return 1
    print(f"OK: pacote gerado em {archive}")
    return 0


def _cmd_build_site(args: argparse.Namespace) -> int:
    for path in (args.junit, args.coverage):
        if not path.is_file():
            print(f"ERRO arquivo não encontrado: {path}", file=sys.stderr)
            return 1
    index = build_site(args.junit, args.coverage, args.output, args.run_id, args.commit)
    print(f"OK: página do relatório gerada em {index}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qa-toolkit",
        description="Valida, checa e empacota a skill de QA cenarios-de-teste.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-skill", help="valida a estrutura do SKILL.md")
    validate.add_argument("path", type=Path, help="pasta da skill ou caminho do SKILL.md")
    validate.set_defaults(func=_cmd_validate_skill)

    lint = sub.add_parser("lint-features", help="verifica arquivos .feature")
    lint.add_argument("paths", type=Path, nargs="+", help="arquivos .feature ou pastas")
    lint.set_defaults(func=_cmd_lint_features)

    package = sub.add_parser("package", help="gera o .zip da skill")
    package.add_argument("path", type=Path, help="pasta da skill")
    package.add_argument("--output", type=Path, default=Path("dist"), help="pasta de saída")
    package.set_defaults(func=_cmd_package)

    site = sub.add_parser("build-site", help="gera a página inicial do relatório")
    site.add_argument("--junit", type=Path, required=True, help="JUnit XML do pytest")
    site.add_argument("--coverage", type=Path, required=True, help="coverage XML")
    site.add_argument("--output", type=Path, default=Path("site"), help="pasta do site")
    site.add_argument("--run-id", default="local", help="ID da execução do CI")
    site.add_argument("--commit", default="local", help="SHA do commit")
    site.set_defaults(func=_cmd_build_site)

    serve = sub.add_parser("serve", help="sobe a API HTTP")
    serve.add_argument("--host", default="127.0.0.1", help="endereço de escuta")
    serve.add_argument("--port", type=int, default=8000, help="porta")
    serve.set_defaults(func=_cmd_serve)

    smoke = sub.add_parser("smoke-test", help="testa uma API já implantada")
    smoke.add_argument("--url", required=True, help="URL base da API")
    smoke.add_argument("--prometheus-url", help="URL do Prometheus, para conferir a coleta de métricas")
    smoke.add_argument("--tentativas", type=int, default=20, help="tentativas até a API ficar saudável")
    smoke.add_argument("--intervalo", type=float, default=3.0, help="segundos entre tentativas")
    smoke.set_defaults(func=_cmd_smoke_test)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
