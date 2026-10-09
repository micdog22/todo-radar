"""Encontra marcações (TODO, FIXME...) dentro de comentários, em várias linguagens."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import PurePosixPath
from typing import Dict, List, Optional, Sequence, Tuple

DEFAULT_TAGS = ("TODO", "FIXME", "HACK", "XXX", "BUG", "OPTIMIZE")
BLOCKS = {"/*": "*/", "<!--": "-->"}
TAG_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")

_FAMILIES: Dict[Tuple[str, ...], str] = {
    ("#",): "py pyw pyi rb sh bash zsh fish pl pm r yaml yml toml cfg conf mk cmake ps1 psm1 nim cr ex exs "
            "tf hcl coffee jl properties dockerfile makefile rakefile gemfile vagrantfile gitignore",
    ("//", "/*"): "c h cc cpp cxx hpp hh cs java js jsx mjs cjs ts tsx mts cts go rs swift kt kts scala dart "
                  "groovy gradle proto zig sol json5 jsonc scss less sass styl",
    ("//", "/*", "#"): "php",
    ("//", "/*", "%"): "m mm",
    ("/*",): "css",
    ("<!--",): "html htm xhtml xml svg md markdown xaml csproj plist",
    ("<!--", "//", "/*"): "vue svelte astro",
    ("--",): "lua hs elm ada adb ads vhd vhdl",
    ("--", "/*"): "sql",
    (";",): "lisp lsp cl el clj cljs cljc edn scm ss rkt asm s",
    (";", "#"): "ini",
    ("%",): "tex sty cls erl hrl",
    ("'",): "vb vbs bas vba frm",
    ("REM", "::"): "bat cmd",
}
MARKERS_BY_TYPE = {ext: markers for markers, names in _FAMILIES.items() for ext in names.split()}
GENERIC_MARKERS = ("#", "//", "/*", "<!--", "--", ";", "%")


@dataclass
class Item:
    path: str
    line: int
    tag: str
    text: str
    owner: str = ""  # quem aparece em TODO(maria)
    author: Optional[str] = None
    timestamp: Optional[float] = None
    source: str = "arquivo"  # git, nao-commitado ou arquivo


def markers_for(path: str) -> Tuple[Tuple[str, ...], bool]:
    """Marcadores de comentário do arquivo e se vale acompanhar comentários de bloco."""
    name = PurePosixPath(path).name.lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else name
    if ext in MARKERS_BY_TYPE:
        return MARKERS_BY_TYPE[ext], True
    if name.startswith("dockerfile"):
        return ("#",), True
    return GENERIC_MARKERS, False


@lru_cache(maxsize=64)
def _patterns(markers: Tuple[str, ...], tags: Tuple[str, ...]):
    tag_alt = "|".join(re.escape(t) for t in sorted(tags, key=len, reverse=True))
    marker_alt = "|".join(
        (r"(?<!\w)" if m[0].isalnum() else "") + re.escape(m) for m in sorted(markers, key=len, reverse=True)
    )
    tail = rf"(?P<tag>{tag_alt})(?:\((?P<owner>[^)]*)\))?(?=[:\s]|$)(?P<rest>.*)"
    line_re = re.compile(rf"(?P<marker>{marker_alt})[ \t*/#!;%'\-]*" + tail)
    inner_re = re.compile(r"^[\s*]*" + tail)  # linhas no meio de um comentário de bloco
    return line_re, inner_re


def _open_block(segment: str, markers: Sequence[str]) -> Optional[str]:
    """Se o trecho abre um comentário de bloco sem fechar, devolve o fechamento esperado."""
    openers = [m for m in markers if m in BLOCKS]
    line_markers = [m for m in markers if m not in BLOCKS]
    pos = 0
    while True:
        found = [(segment.find(o, pos), o) for o in openers]
        found = [(i, o) for i, o in found if i >= 0]
        if not found:
            return None
        index, opener = min(found)
        if any(0 <= segment.find(m, pos) < index for m in line_markers):
            return None  # o resto da linha já é comentário de linha
        close = segment.find(BLOCKS[opener], index + len(opener))
        if close < 0:
            return BLOCKS[opener]
        pos = close + len(BLOCKS[opener])


def _make_item(match: re.Match, path: str, number: int, closer: Optional[str]) -> Item:
    rest = match.group("rest")
    if closer and closer in rest:
        rest = rest[: rest.index(closer)]
    text = rest.strip().lstrip(":-").strip()
    return Item(path, number, match.group("tag"), text, (match.group("owner") or "").strip())


def extract(text: str, path: str, tags: Sequence[str] = DEFAULT_TAGS) -> List[Item]:
    markers, track_blocks = markers_for(path)
    line_re, inner_re = _patterns(tuple(markers), tuple(tags))
    items: List[Item] = []
    closer: Optional[str] = None
    for number, line in enumerate(text.splitlines(), 1):
        segment = line
        if closer:
            end = line.find(closer)
            match = inner_re.match(line if end < 0 else line[:end])
            if match:
                items.append(_make_item(match, path, number, None))
            if end < 0:
                continue
            segment, closer = line[end + len(closer):], None
        match = line_re.search(segment)
        if match:
            items.append(_make_item(match, path, number, BLOCKS.get(match.group("marker"))))
        if track_blocks:
            closer = _open_block(segment, markers)
    return items


def parse_tags(raw: Optional[str]) -> Tuple[str, ...]:
    if not raw:
        return DEFAULT_TAGS
    tags = tuple(dict.fromkeys(t.strip().upper() for t in raw.split(",") if t.strip()))
    invalid = [t for t in tags if not TAG_RE.match(t)]
    if not tags or invalid:
        raise ValueError(f"tags inválidas: {', '.join(invalid) or raw!r} (use letras, números, - e _)")
    return tags
