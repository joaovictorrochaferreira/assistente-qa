from datetime import UTC, datetime

import pytest

from qa_toolkit.site_builder import ResultSummary, build_site, read_coverage, read_junit, render_index

JUNIT_TESTSUITES = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="10" failures="1" errors="1" skipped="2"/>
  <testsuite name="outra" tests="5" failures="0" errors="0" skipped="0"/>
</testsuites>
"""
JUNIT_SINGLE = '<testsuite name="pytest" tests="3" failures="0" errors="0" skipped="0"/>'
COVERAGE = '<?xml version="1.0" ?><coverage line-rate="0.9567" branch-rate="0.9"></coverage>'


def test_read_junit_soma_todas_as_suites(tmp_path):
    file = tmp_path / "junit.xml"
    file.write_text(JUNIT_TESTSUITES, encoding="utf-8")
    summary = read_junit(file)
    assert summary == ResultSummary(total=15, failures=1, errors=1, skipped=2)
    assert summary.passed == 11
    assert not summary.ok


def test_read_junit_com_suite_unica(tmp_path):
    file = tmp_path / "junit.xml"
    file.write_text(JUNIT_SINGLE, encoding="utf-8")
    assert read_junit(file).ok


def test_read_coverage_em_percentual(tmp_path):
    file = tmp_path / "coverage.xml"
    file.write_text(COVERAGE, encoding="utf-8")
    assert read_coverage(file) == pytest.approx(95.7)


def test_resumo_sem_testes_nao_e_aprovado():
    assert not ResultSummary(0, 0, 0, 0).ok


def test_render_index_aprovado():
    page = render_index(
        ResultSummary(20, 0, 0, 1),
        93.25,
        run_id="123",
        commit="abcdef1234567890",
        generated_at=datetime(2026, 11, 12, 10, 30, tzinfo=UTC),
    )
    assert 'data-testid="status">Aprovado<' in page
    assert 'data-testid="total">20<' in page
    assert 'data-testid="passed">19<' in page
    assert 'data-testid="failed">0<' in page
    assert 'data-testid="coverage">93.2%<' in page or 'data-testid="coverage">93.3%<' in page
    assert 'data-testid="run-id">123<' in page
    assert ">abcdef123456<" in page
    assert "12/11/2026 10:30 UTC" in page


def test_render_index_reprovado_e_escapa_html():
    page = render_index(ResultSummary(5, 2, 1, 0), 50.0, run_id="<script>")
    assert 'data-testid="status">Reprovado<' in page
    assert 'data-testid="failed">3<' in page
    assert "<script>" not in page


def test_build_site_escreve_index(tmp_path):
    junit = tmp_path / "junit.xml"
    junit.write_text(JUNIT_SINGLE, encoding="utf-8")
    coverage = tmp_path / "coverage.xml"
    coverage.write_text(COVERAGE, encoding="utf-8")
    index = build_site(junit, coverage, tmp_path / "site", run_id="42", commit="abc")
    assert index == tmp_path / "site" / "index.html"
    assert 'data-testid="run-id">42<' in index.read_text(encoding="utf-8")
