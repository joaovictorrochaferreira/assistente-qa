from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
SKILL_FIXTURE = FIXTURES / "skills" / "cenarios-de-teste"
VALID_FEATURES = FIXTURES / "features" / "validos"
INVALID_FEATURES = FIXTURES / "features" / "invalidos"
REAL_SKILL = ROOT / "skill" / "cenarios-de-teste"


@pytest.hookimpl(optionalhook=True)
def pytest_html_report_title(report):
    report.title = "Relatório de testes do qa-toolkit"
