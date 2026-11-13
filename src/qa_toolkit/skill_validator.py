"""Validação estrutural de uma skill (pasta com SKILL.md).

Regras verificadas:
- frontmatter YAML com ``name`` e ``description`` válidos;
- ``name`` igual ao nome da pasta da skill;
- presença das etapas obrigatórias (``### Etapa N: ...``), sem repetição e em ordem;
- presença das seções obrigatórias de nível 2;
- links internos apontando para arquivos e âncoras existentes dentro da skill.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import yaml

from qa_toolkit.issues import Issue

SKILL_FILE = "SKILL.md"
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NAME_MAX_LENGTH = 64
DESCRIPTION_MAX_LENGTH = 1024
REQUIRED_STAGES: tuple[int, ...] = tuple(range(1, 8))
REQUIRED_SECTIONS: tuple[str, ...] = (
    "Fontes de informação",
    "Fluxo de trabalho",
    "Formato de saída",
)

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_STAGE = re.compile(r"^Etapa\s+(\d+)\s*:")
_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.IGNORECASE)


def resolve_skill_file(path: Path) -> Path:
    """Aceita a pasta da skill ou o próprio SKILL.md e devolve o caminho do arquivo."""
    return path / SKILL_FILE if path.is_dir() else path


def validate_skill(
    path: Path,
    required_stages: tuple[int, ...] = REQUIRED_STAGES,
    required_sections: tuple[str, ...] = REQUIRED_SECTIONS,
) -> list[Issue]:
    """Valida a skill e devolve a lista de problemas (vazia quando está tudo certo)."""
    skill_file = resolve_skill_file(path)
    if not skill_file.is_file():
        return [Issue(skill_file, f"arquivo {SKILL_FILE} não encontrado")]

    text = skill_file.read_text(encoding="utf-8-sig")
    frontmatter, body_lines, body_offset, issues = _split_frontmatter(skill_file, text)
    if frontmatter is not None:
        issues += _check_frontmatter(skill_file, frontmatter)

    headings = list(_iter_headings(body_lines, body_offset))
    issues += _check_stages(skill_file, headings, required_stages)
    issues += _check_sections(skill_file, headings, required_sections)
    issues += _check_links(skill_file, body_lines, body_offset, headings)
    return issues


def _split_frontmatter(skill_file: Path, text: str) -> tuple[dict | None, list[str], int, list[Issue]]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, lines, 0, [Issue(skill_file, "frontmatter ausente: o arquivo deve começar com ---", 1)]

    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            raw = "\n".join(lines[1:index])
            body = lines[index + 1 :]
            offset = index + 1
            try:
                data = yaml.safe_load(raw)
            except yaml.YAMLError as error:
                return None, body, offset, [Issue(skill_file, f"frontmatter com YAML inválido: {error}", 1)]
            if not isinstance(data, dict):
                return None, body, offset, [Issue(skill_file, "frontmatter deve ser um mapa chave: valor", 1)]
            return data, body, offset, []

    return None, lines, 0, [Issue(skill_file, "frontmatter sem o --- de fechamento", 1)]


def _check_frontmatter(skill_file: Path, data: dict) -> list[Issue]:
    issues: list[Issue] = []
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        issues.append(Issue(skill_file, "campo 'name' ausente ou vazio no frontmatter", 1))
    else:
        if not NAME_PATTERN.match(name):
            issues.append(Issue(skill_file, f"'name' deve usar só minúsculas, números e hífens: {name!r}", 1))
        if len(name) > NAME_MAX_LENGTH:
            issues.append(Issue(skill_file, f"'name' passa de {NAME_MAX_LENGTH} caracteres", 1))
        folder = skill_file.parent.name
        if name != folder:
            issues.append(
                Issue(skill_file, f"'name' ({name}) difere do nome da pasta da skill ({folder})", 1)
            )

    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        issues.append(Issue(skill_file, "campo 'description' ausente ou vazio no frontmatter", 1))
    elif len(description) > DESCRIPTION_MAX_LENGTH:
        issues.append(Issue(skill_file, f"'description' passa de {DESCRIPTION_MAX_LENGTH} caracteres", 1))
    return issues


def _iter_lines_outside_fences(lines: list[str], offset: int) -> Iterator[tuple[int, str]]:
    """Percorre as linhas ignorando blocos de código cercados por ``` ou ~~~."""
    fence: str | None = None
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        marker = stripped[:3]
        if marker in ("```", "~~~"):
            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None
            continue
        if fence is None:
            yield offset + index + 1, line


def _iter_headings(lines: list[str], offset: int) -> Iterator[tuple[int, int, str]]:
    for line_number, line in _iter_lines_outside_fences(lines, offset):
        match = _HEADING.match(line)
        if match:
            yield line_number, len(match.group(1)), match.group(2)


def _check_stages(
    skill_file: Path, headings: list[tuple[int, int, str]], required: tuple[int, ...]
) -> list[Issue]:
    issues: list[Issue] = []
    found: list[int] = []
    for line_number, _level, title in headings:
        match = _STAGE.match(title)
        if not match:
            continue
        number = int(match.group(1))
        if number in found:
            issues.append(Issue(skill_file, f"Etapa {number} aparece mais de uma vez", line_number))
        elif found and number < found[-1]:
            issues.append(
                Issue(
                    skill_file,
                    f"Etapa {number} está fora de ordem (veio depois da Etapa {found[-1]})",
                    line_number,
                )
            )
        found.append(number)

    for number in required:
        if number not in found:
            issues.append(Issue(skill_file, f"Etapa obrigatória ausente: '### Etapa {number}: ...'"))
    return issues


def _check_sections(
    skill_file: Path, headings: list[tuple[int, int, str]], required: tuple[str, ...]
) -> list[Issue]:
    titles = [title.casefold() for _line, level, title in headings if level == 2]
    return [
        Issue(skill_file, f"seção obrigatória ausente: '## {section}'")
        for section in required
        if not any(title.startswith(section.casefold()) for title in titles)
    ]


def slugify(title: str) -> str:
    """Gera a âncora no mesmo padrão usado pelo GitHub para títulos Markdown."""
    text = re.sub(r"[`*_~]", "", title).strip().casefold()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def _anchors(headings: list[tuple[int, int, str]]) -> set[str]:
    seen: dict[str, int] = {}
    anchors: set[str] = set()
    for _line, _level, title in headings:
        slug = slugify(title)
        count = seen.get(slug, 0)
        anchors.add(slug if count == 0 else f"{slug}-{count}")
        seen[slug] = count + 1
    return anchors


def _anchors_of_file(path: Path) -> set[str]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    return _anchors(list(_iter_headings(lines, 0)))


def _check_links(
    skill_file: Path,
    lines: list[str],
    offset: int,
    headings: list[tuple[int, int, str]],
) -> list[Issue]:
    issues: list[Issue] = []
    skill_dir = skill_file.parent.resolve()
    own_anchors = _anchors(headings)

    for line_number, line in _iter_lines_outside_fences(lines, offset):
        # Ignora trechos de código inline, que costumam conter exemplos e não links reais.
        clean = re.sub(r"`[^`]*`", "", line)
        for target in _LINK.findall(clean):
            if _EXTERNAL.match(target):
                continue
            file_part, _, anchor = target.partition("#")
            if not file_part:
                if anchor not in own_anchors:
                    issues.append(Issue(skill_file, f"âncora interna inexistente: #{anchor}", line_number))
                continue

            resolved = (skill_file.parent / file_part).resolve()
            if not resolved.is_relative_to(skill_dir):
                issues.append(
                    Issue(skill_file, f"link aponta para fora da pasta da skill: {target}", line_number)
                )
            elif not resolved.exists():
                issues.append(Issue(skill_file, f"link para arquivo inexistente: {target}", line_number))
            elif anchor and resolved.suffix.lower() == ".md" and anchor not in _anchors_of_file(resolved):
                issues.append(
                    Issue(skill_file, f"âncora inexistente no arquivo de destino: {target}", line_number)
                )
    return issues
