"""Varre a pasta, extrai as marcações e completa autor e idade com o git blame."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import List, Optional, Sequence

from . import gitinfo
from .extract import DEFAULT_TAGS, Item, extract

MAX_SIZE = 2 * 1024 * 1024
SKIP_DIRS = {
    ".git", "node_modules", "venv", ".venv", "dist", "build", "vendor", "__pycache__",
    ".hg", ".svn", ".tox", ".mypy_cache", ".pytest_cache",
}


@dataclass
class ScanResult:
    items: List[Item] = field(default_factory=list)
    files: int = 0
    skipped: int = 0  # binários, grandes demais ou ilegíveis
    used_git: bool = False


def walk_files(folder: Path) -> List[str]:
    """Lista os arquivos sem git, pulando pastas de dependências e de build."""
    found = []
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = sorted(
            d for d in dirnames if d not in SKIP_DIRS and not os.path.islink(os.path.join(dirpath, d))
        )
        for name in sorted(filenames):
            full = Path(dirpath) / name
            if not full.is_symlink():
                found.append(full.relative_to(folder).as_posix())
    return found


def read_text(path: Path) -> Optional[str]:
    """Conteúdo do arquivo, ou None se for binário, maior que 2 MB ou ilegível."""
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_SIZE:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")  # código antigo em latin-1/cp1252


def _attach_blame(folder: Path, path: str, items: List[Item], use_git: bool) -> None:
    try:
        mtime: Optional[float] = (folder / path).stat().st_mtime
    except OSError:
        mtime = None
    lines = gitinfo.blame(folder, path) if use_git else None
    for item in items:
        info = lines.get(item.line) if lines else None
        if info is not None and info.committed:
            item.author, item.timestamp, item.source = info.author, info.timestamp, "git"
        else:
            # Linha ainda não commitada, arquivo novo ou pasta sem git: a data do
            # arquivo é a melhor estimativa que existe.
            item.timestamp = mtime
            item.source = "nao-commitado" if use_git else "arquivo"


def scan(folder, tags: Sequence[str] = DEFAULT_TAGS, use_git: bool = True) -> ScanResult:
    folder = Path(folder)
    result = ScanResult()
    files = None
    if use_git and gitinfo.is_git_repo(folder):
        files = gitinfo.list_files(folder)
    result.used_git = files is not None
    if files is None:
        files = walk_files(folder)
    else:
        # Dependências e builds ficam de fora mesmo quando não estão no .gitignore.
        files = [f for f in files if not SKIP_DIRS.intersection(PurePosixPath(f).parts[:-1])]
    for path in files:
        text = read_text(folder / path)
        if text is None:
            result.skipped += 1
            continue
        result.files += 1
        found = extract(text, path, tags)
        if found:
            _attach_blame(folder, path, found, result.used_git)
            result.items.extend(found)
    return result
