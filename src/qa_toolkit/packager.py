"""Empacotamento da skill em um .zip pronto para instalar."""

from __future__ import annotations

import zipfile
from pathlib import Path

from qa_toolkit.issues import Issue
from qa_toolkit.skill_validator import resolve_skill_file, validate_skill

# Data fixa nos arquivos do zip: o mesmo conteúdo sempre gera o mesmo zip (build reproduzível).
_FIXED_DATE = (1980, 1, 1, 0, 0, 0)
_IGNORED_NAMES = {"__pycache__", ".DS_Store", "Thumbs.db"}


class PackagingError(Exception):
    """A skill tem problemas de validação e não deve ser empacotada."""

    def __init__(self, issues: list[Issue]):
        self.issues = issues
        super().__init__(f"skill inválida: {len(issues)} problema(s) encontrado(s)")


def _skill_files(skill_dir: Path) -> list[Path]:
    files = []
    for path in sorted(skill_dir.rglob("*")):
        relative = path.relative_to(skill_dir)
        if not path.is_file():
            continue
        if any(part.startswith(".") or part in _IGNORED_NAMES for part in relative.parts):
            continue
        files.append(path)
    return files


def build_skill_zip(skill_path: Path, output_dir: Path) -> Path:
    """Valida a skill e gera ``<output_dir>/<nome-da-skill>.zip``.

    Dentro do zip, os arquivos ficam em uma pasta com o nome da skill,
    que é o formato esperado na instalação.
    """
    skill_dir = resolve_skill_file(skill_path).parent
    issues = validate_skill(skill_dir)
    if issues:
        raise PackagingError(issues)

    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"{skill_dir.name}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for file in _skill_files(skill_dir):
            arcname = f"{skill_dir.name}/{file.relative_to(skill_dir).as_posix()}"
            info = zipfile.ZipInfo(arcname, date_time=_FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            bundle.writestr(info, file.read_bytes())
    return archive
