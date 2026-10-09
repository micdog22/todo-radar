"""Integração com o git: lista de arquivos (respeitando o .gitignore) e git blame."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

_HEADER_RE = re.compile(r"^([0-9a-f]{40}|[0-9a-f]{64}) \d+ (\d+)(?: \d+)?$")


@dataclass
class BlameLine:
    author: Optional[str]
    timestamp: Optional[int]
    committed: bool


def _git(folder: Path, *args: str, timeout: int = 120) -> Optional[bytes]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(folder), *args],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None  # git não instalado ou travado: segue sem ele
    return proc.stdout if proc.returncode == 0 else None


def is_git_repo(folder: Path) -> bool:
    output = _git(folder, "rev-parse", "--is-inside-work-tree", timeout=30)
    return output is not None and output.strip() == b"true"


def list_files(folder: Path) -> Optional[List[str]]:
    """Arquivos versionados e novos (não ignorados), relativos à pasta."""
    output = _git(folder, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if output is None:
        return None
    return sorted({os.fsdecode(name) for name in output.split(b"\0") if name})


def parse_porcelain(output: str) -> Dict[int, BlameLine]:
    """Lê a saída de `git blame --line-porcelain`: autor e data de cada linha."""
    lines: Dict[int, BlameLine] = {}
    current: Optional[int] = None
    sha = author = None
    timestamp: Optional[int] = None
    for row in output.split("\n"):
        if row.startswith("\t"):
            if current is not None:
                committed = sha.strip("0") != ""
                lines[current] = BlameLine(author if committed else None, timestamp if committed else None, committed)
            current = None
            continue
        header = _HEADER_RE.match(row)
        if header:
            sha, current = header.group(1), int(header.group(2))
            author, timestamp = None, None
        elif row.startswith("author "):
            author = row[len("author "):]
        elif row.startswith("author-time "):
            timestamp = int(row[len("author-time "):])
    return lines


def blame(folder: Path, path: str) -> Optional[Dict[int, BlameLine]]:
    """Autor e data por linha; None se o arquivo não está no git (ou o blame falhou)."""
    output = _git(folder, "blame", "--line-porcelain", "--", path)
    if output is None:
        return None
    return parse_porcelain(output.decode("utf-8", errors="replace"))
