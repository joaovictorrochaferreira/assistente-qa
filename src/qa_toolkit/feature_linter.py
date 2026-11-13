"""Linter dos arquivos .feature no formato documental da skill cenarios-de-teste.

O formato segue a seção "Formato de saída (obrigatório)" da skill:

    CONTEXTO
    DADO que está logado na plataforma
    E com o perfil "Administrador"

    CT001 - Login com credenciais válidas
    DADO que está na tela de login
    QUANDO são informados e-mail e senha corretos
    ENTÃO é feito o redirecionamento para a tela inicial

Regras verificadas:
- existe um bloco CONTEXTO (Background) antes do primeiro cenário;
- cada cenário tem título ``CTnnn - descrição``, com IDs únicos e em sequência;
- palavras-chave em MAIÚSCULAS (DADO, QUANDO, ENTÃO, E), nunca "AND";
- cada cenário tem DADO, QUANDO e ENTÃO, nessa ordem, e nenhum passo vazio;
- o CONTEXTO só tem passos de estado (DADO e E);
- sem indentação e sem linha em branco entre os passos de um mesmo bloco.
Linhas iniciadas por ``#`` são comentários e são ignoradas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from qa_toolkit.issues import Issue

KEYWORDS = ("DADO", "QUANDO", "ENTÃO", "E")
_PHASE = {"DADO": 0, "QUANDO": 1, "ENTÃO": 2}
_PHASE_NAME = {0: "DADO", 1: "QUANDO", 2: "ENTÃO"}

_CONTEXT = re.compile(r"^CONTEXTO(?:\s*[-:]\s*(\S.*))?$")
_SCENARIO = re.compile(r"^CT(\d{3,})\s+-\s+(\S.*)$")
_SCENARIO_LIKE = re.compile(r"^CT\d+\b")
_STEP = re.compile(r"^(DADO|QUANDO|ENTÃO|E)(?:\s+(.*))?$")
_GHERKIN_HEADERS = re.compile(
    r"^(cenário|cenario|scenario|esquema do cenário|contexto|background|funcionalidade|feature)\s*:",
    re.IGNORECASE,
)
_KEYWORD_VARIANTS = {
    "dado": "DADO",
    "dada": "DADO",
    "given": "DADO",
    "quando": "QUANDO",
    "when": "QUANDO",
    "então": "ENTÃO",
    "entao": "ENTÃO",
    "then": "ENTÃO",
    "e": "E",
    "and": "E",
    "mas": "E",
    "but": "E",
}


@dataclass
class _Step:
    keyword: str
    text: str
    line: int


@dataclass
class _Block:
    kind: str  # "contexto" ou "cenario"
    label: str
    line: int
    number: int | None = None
    steps: list[_Step] = field(default_factory=list)


def lint_file(path: Path) -> list[Issue]:
    """Verifica um arquivo .feature e devolve os problemas encontrados."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return [Issue(path, "arquivo não está em UTF-8")]

    issues: list[Issue] = []
    blocks: list[_Block] = []
    current: _Block | None = None
    blank_after_step = False

    for line_number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            if current is not None and current.steps:
                blank_after_step = True
            continue
        if raw.lstrip().startswith("#"):
            continue

        line = raw.strip()
        if raw != raw.lstrip():
            issues.append(
                Issue(path, "linha com indentação: o formato não usa espaços ou tabs no início", line_number)
            )

        header = _parse_header(line, line_number)
        if header is not None:
            current = header
            blocks.append(current)
            blank_after_step = False
            continue

        if _GHERKIN_HEADERS.match(line):
            issues.append(
                Issue(path, "cabeçalho fora do formato: use 'CONTEXTO' ou 'CT001 - Título'", line_number)
            )
            continue
        if _SCENARIO_LIKE.match(line):
            issues.append(
                Issue(path, "título de cenário fora do formato 'CT001 - Título descritivo'", line_number)
            )
            continue

        step = _parse_step(path, line, line_number, issues)
        if step is None:
            continue
        if current is None:
            issues.append(Issue(path, "passo fora de um bloco CONTEXTO ou cenário", line_number))
            continue
        if blank_after_step:
            issues.append(Issue(path, f"linha em branco entre os passos de {current.label}", line_number))
            blank_after_step = False
        current.steps.append(step)

    issues += _check_blocks(path, blocks)
    return sorted(issues, key=lambda issue: issue.line or 0)


def _parse_header(line: str, line_number: int) -> _Block | None:
    context = _CONTEXT.match(line)
    if context:
        name = context.group(1)
        return _Block("contexto", f"CONTEXTO {name}" if name else "CONTEXTO", line_number)
    scenario = _SCENARIO.match(line)
    if scenario:
        number = int(scenario.group(1))
        return _Block("cenario", f"CT{scenario.group(1)}", line_number, number=number)
    return None


def _parse_step(path: Path, line: str, line_number: int, issues: list[Issue]) -> _Step | None:
    match = _STEP.match(line)
    if match:
        keyword, text = match.group(1), (match.group(2) or "").strip()
        if not text:
            issues.append(Issue(path, f"passo vazio: '{keyword}' sem descrição", line_number))
        return _Step(keyword, text, line_number)

    first_word = line.split(maxsplit=1)[0]
    expected = _KEYWORD_VARIANTS.get(first_word.casefold())
    if expected is not None:
        issues.append(
            Issue(
                path,
                f"palavra-chave '{first_word}' fora do padrão: use '{expected}' em MAIÚSCULAS",
                line_number,
            )
        )
        rest = line[len(first_word) :].strip()
        return _Step(expected, rest, line_number)

    issues.append(Issue(path, f"linha não reconhecida: {line[:60]!r}", line_number))
    return None


def _check_blocks(path: Path, blocks: list[_Block]) -> list[Issue]:
    issues: list[Issue] = []
    contexts = [block for block in blocks if block.kind == "contexto"]
    scenarios = [block for block in blocks if block.kind == "cenario"]

    if not contexts:
        issues.append(Issue(path, "arquivo sem bloco CONTEXTO (Background)", 1))
    elif scenarios and scenarios[0].line < contexts[0].line:
        issues.append(Issue(path, "o CONTEXTO deve vir antes do primeiro cenário", contexts[0].line))
    if not scenarios:
        issues.append(Issue(path, "arquivo sem cenários (CT001 - ...)", 1))

    for block in contexts:
        issues += _check_context(path, block)
    for block in scenarios:
        issues += _check_scenario(path, block)
    issues += _check_ids(path, scenarios)
    return issues


def _check_context(path: Path, block: _Block) -> list[Issue]:
    if not block.steps:
        return [Issue(path, f"{block.label} sem passos", block.line)]
    issues: list[Issue] = []
    if block.steps[0].keyword != "DADO":
        issues.append(Issue(path, f"{block.label} deve começar com DADO", block.steps[0].line))
    issues += [
        Issue(path, f"{block.label} só deve ter passos de estado (DADO/E), achado {step.keyword}", step.line)
        for step in block.steps
        if step.keyword in ("QUANDO", "ENTÃO")
    ]
    return issues


def _check_scenario(path: Path, block: _Block) -> list[Issue]:
    if not block.steps:
        return [Issue(path, f"{block.label} sem passos", block.line)]

    issues: list[Issue] = []
    if block.steps[0].keyword == "E":
        issues.append(Issue(path, f"{block.label} não pode começar com E", block.steps[0].line))

    phase = -1
    for step in block.steps:
        if step.keyword == "E":
            continue
        step_phase = _PHASE[step.keyword]
        if step_phase < phase:
            issues.append(
                Issue(
                    path,
                    f"{block.label}: {step.keyword} após {_PHASE_NAME[phase]} (ordem: DADO, QUANDO, ENTÃO)",
                    step.line,
                )
            )
        phase = max(phase, step_phase)

    present = {step.keyword for step in block.steps}
    issues += [
        Issue(path, f"{block.label} sem passo {keyword}", block.line)
        for keyword in ("DADO", "QUANDO", "ENTÃO")
        if keyword not in present
    ]
    return issues


def _check_ids(path: Path, scenarios: list[_Block]) -> list[Issue]:
    issues: list[Issue] = []
    seen: dict[int, int] = {}
    for expected, block in enumerate(scenarios, start=1):
        assert block.number is not None
        if block.number in seen:
            issues.append(
                Issue(path, f"ID duplicado: {block.label} já usado na linha {seen[block.number]}", block.line)
            )
        else:
            seen[block.number] = block.line
            if block.number != expected:
                issues.append(
                    Issue(
                        path,
                        f"ID fora de sequência: esperado CT{expected:03d}, achado {block.label}",
                        block.line,
                    )
                )
    return issues


def collect_feature_files(paths: list[Path]) -> list[Path]:
    """Expande pastas em arquivos .feature, mantendo uma ordem estável."""
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.rglob("*.feature")))
        else:
            files.append(path)
    return files


def lint_paths(paths: list[Path]) -> tuple[list[Path], list[Issue]]:
    """Verifica todos os .feature encontrados e devolve (arquivos, problemas)."""
    files = collect_feature_files(paths)
    issues: list[Issue] = []
    for file in files:
        if not file.is_file():
            issues.append(Issue(file, "arquivo não encontrado"))
            continue
        issues += lint_file(file)
    return files, issues
