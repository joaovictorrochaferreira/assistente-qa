"""Gera a página inicial do relatório publicado no GitHub Pages.

A página resume o resultado dos testes (JUnit XML) e a cobertura (coverage XML)
e aponta para os relatórios completos, gerados pelo pytest-html e pelo coverage.py.
Os elementos importantes têm ``data-testid`` para serem verificados pelo teste E2E.
"""

from __future__ import annotations

import html
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

TEST_REPORT_PATH = "relatorio/index.html"
COVERAGE_REPORT_PATH = "cobertura/index.html"


@dataclass(frozen=True)
class ResultSummary:
    total: int
    failures: int
    errors: int
    skipped: int

    @property
    def passed(self) -> int:
        return self.total - self.failures - self.errors - self.skipped

    @property
    def ok(self) -> bool:
        return self.total > 0 and self.failures == 0 and self.errors == 0


def read_junit(path: Path) -> ResultSummary:
    """Soma os contadores de todas as suítes de um JUnit XML."""
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in totals:
            totals[key] += int(suite.get(key, 0))
    return ResultSummary(totals["tests"], totals["failures"], totals["errors"], totals["skipped"])


def read_coverage(path: Path) -> float:
    """Lê a cobertura de linhas (em %) de um coverage XML no formato Cobertura."""
    root = ET.parse(path).getroot()
    return round(float(root.get("line-rate", 0)) * 100, 1)


def render_index(
    summary: ResultSummary,
    coverage: float,
    run_id: str = "local",
    commit: str = "local",
    generated_at: datetime | None = None,
) -> str:
    generated = (generated_at or datetime.now(UTC)).strftime("%d/%m/%Y %H:%M UTC")
    status = "Aprovado" if summary.ok else "Reprovado"
    status_class = "ok" if summary.ok else "falha"
    esc = html.escape
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Relatório de qualidade | assistente-qa</title>
<style>
  :root {{ color-scheme: light dark; --ok: #1a7f37; --falha: #cf222e; }}
  body {{ font-family: system-ui, sans-serif; max-width: 760px; margin: 2rem auto; padding: 0 1rem; }}
  .status {{ font-weight: 700; }}
  .status.ok {{ color: var(--ok); }}
  .status.falha {{ color: var(--falha); }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ text-align: left; padding: .4rem .6rem; border-bottom: 1px solid #8884; }}
  footer {{ margin-top: 2rem; font-size: .85rem; opacity: .75; }}
</style>
</head>
<body>
<h1>Relatório de qualidade do assistente-qa</h1>
<p>Situação: <span class="status {status_class}" data-testid="status">{status}</span></p>
<table>
  <tr><th>Testes executados</th><td data-testid="total">{summary.total}</td></tr>
  <tr><th>Aprovados</th><td data-testid="passed">{summary.passed}</td></tr>
  <tr><th>Falhas</th><td data-testid="failed">{summary.failures + summary.errors}</td></tr>
  <tr><th>Ignorados</th><td data-testid="skipped">{summary.skipped}</td></tr>
  <tr><th>Cobertura de linhas</th><td data-testid="coverage">{coverage:.1f}%</td></tr>
</table>
<h2>Relatórios completos</h2>
<ul>
  <li><a data-testid="link-relatorio" href="{TEST_REPORT_PATH}">Testes (pytest-html)</a></li>
  <li><a data-testid="link-cobertura" href="{COVERAGE_REPORT_PATH}">Cobertura (coverage.py)</a></li>
</ul>
<footer>
  Execução <span data-testid="run-id">{esc(run_id)}</span>,
  commit <code data-testid="commit">{esc(commit[:12])}</code>, gerado em {generated}.
</footer>
</body>
</html>
"""


def build_site(
    junit: Path,
    coverage_xml: Path,
    output_dir: Path,
    run_id: str = "local",
    commit: str = "local",
) -> Path:
    """Escreve ``index.html`` em ``output_dir`` e devolve o caminho do arquivo."""
    summary = read_junit(junit)
    coverage = read_coverage(coverage_xml)
    output_dir.mkdir(parents=True, exist_ok=True)
    index = output_dir / "index.html"
    index.write_text(render_index(summary, coverage, run_id, commit), encoding="utf-8")
    return index
