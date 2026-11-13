"""Estrutura comum para os problemas encontrados pelos validadores."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Issue:
    """Um problema encontrado em um arquivo, com a linha quando ela é conhecida."""

    path: Path
    message: str
    line: int | None = None

    def __str__(self) -> str:
        location = f"{self.path}:{self.line}" if self.line else str(self.path)
        return f"{location}: {self.message}"
