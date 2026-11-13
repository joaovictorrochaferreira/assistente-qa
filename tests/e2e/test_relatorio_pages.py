"""Testes E2E do relatório publicado no GitHub Pages.

Execução (o CI passa a URL publicada pelo job de deploy):
    pytest tests/e2e --base-url https://<usuario>.github.io/assistente-qa/ --browser chromium

Com EXPECTED_RUN_ID definido, o teste espera até a página mostrar essa execução,
para não validar uma versão antiga ainda guardada no cache do Pages.
"""

from __future__ import annotations

import os
import re
import time

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e

EXPECTED_RUN_ID = os.environ.get("EXPECTED_RUN_ID", "")
WAIT_SECONDS = int(os.environ.get("E2E_WAIT_SECONDS", "180"))
MIN_COVERAGE = 90.0


@pytest.fixture
def home(page: Page, base_url: str | None) -> Page:
    if not base_url:
        pytest.skip("informe --base-url com a URL do relatório no GitHub Pages")
    root = base_url.rstrip("/") + "/"

    deadline = time.monotonic() + WAIT_SECONDS
    attempt = 0
    while True:
        attempt += 1
        # O parâmetro muda a cada tentativa para evitar o cache da CDN do Pages.
        response = page.goto(f"{root}?run={EXPECTED_RUN_ID or 'local'}&tentativa={attempt}")
        assert response is not None, "o Pages não respondeu"
        assert response.ok, f"o Pages respondeu com status {response.status}"
        if not EXPECTED_RUN_ID:
            return page
        if page.get_by_test_id("run-id").inner_text().strip() == EXPECTED_RUN_ID:
            return page
        if time.monotonic() > deadline:
            pytest.fail(f"o Pages não publicou a execução {EXPECTED_RUN_ID} em {WAIT_SECONDS}s")
        time.sleep(10)


def test_pagina_inicial_mostra_execucao_aprovada(home: Page):
    expect(home).to_have_title(re.compile("Relatório de qualidade"))
    expect(home.get_by_test_id("status")).to_have_text("Aprovado")
    expect(home.get_by_test_id("failed")).to_have_text("0")
    assert int(home.get_by_test_id("total").inner_text()) > 0


def test_cobertura_publicada_atende_o_minimo(home: Page):
    coverage = float(home.get_by_test_id("coverage").inner_text().rstrip("%"))
    assert coverage >= MIN_COVERAGE


def test_link_abre_o_relatorio_de_testes(home: Page):
    home.get_by_test_id("link-relatorio").click()
    expect(home).to_have_url(re.compile(r"relatorio/(index\.html)?(\?.*)?$"))
    expect(home).to_have_title(re.compile("Relatório de testes do qa-toolkit"))


def test_link_abre_o_relatorio_de_cobertura(home: Page):
    home.get_by_test_id("link-cobertura").click()
    expect(home).to_have_url(re.compile(r"cobertura/(index\.html)?(\?.*)?$"))
    expect(home.get_by_text("qa_toolkit", exact=False).first).to_be_visible()
