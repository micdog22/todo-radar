"""Saídas: tabela no terminal, Markdown e JSON, com agrupamento opcional."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from .age import format_age
from .extract import DEFAULT_TAGS, Item

TAG_COLORS = {"FIXME": "31", "BUG": "31", "TODO": "33", "HACK": "35", "XXX": "35", "OPTIMIZE": "36"}


def age_days(item: Item, now: float) -> Optional[float]:
    if item.timestamp is None:
        return None
    return max(0.0, (now - item.timestamp) / 86400)


def sort_items(items: Sequence[Item]) -> List[Item]:
    """Mais antigas primeiro; sem data no fim."""
    return sorted(items, key=lambda i: (i.timestamp is None, i.timestamp or 0, i.path, i.line))


def filter_older_than(items: Sequence[Item], days: int, now: float) -> List[Item]:
    return [i for i in items if i.timestamp is not None and age_days(i, now) >= days]


def author_label(item: Item) -> str:
    if item.author:
        return item.author
    return "(não commitado)" if item.source == "nao-commitado" else "-"


def tag_label(item: Item) -> str:
    return f"{item.tag}({item.owner})" if item.owner else item.tag


def plural(count: int, singular: str, plural_form: str) -> str:
    return f"{count} {singular if count == 1 else plural_form}"


def group_items(items: Sequence[Item], by: str, tags: Sequence[str] = DEFAULT_TAGS) -> List[Tuple[str, List[Item]]]:
    keys = {"arquivo": lambda i: i.path, "tag": lambda i: i.tag, "autor": author_label}
    buckets: Dict[str, List[Item]] = {}
    for item in items:
        buckets.setdefault(keys[by](item), []).append(item)
    if by == "arquivo":
        order = sorted(buckets)
    elif by == "tag":
        order = sorted(buckets, key=lambda t: (list(tags).index(t) if t in tags else len(tags), t))
    else:
        order = sorted(buckets, key=lambda a: (-len(buckets[a]), a.casefold()))
    return [(name, buckets[name]) for name in order]


def summary_line(items: Sequence[Item]) -> str:
    if not items:
        return "Nenhuma marcação encontrada."
    files = len({i.path for i in items})
    counts = ", ".join(f"{tag} {n}" for tag, n in Counter(i.tag for i in items).most_common())
    return f"{plural(len(items), 'marcação', 'marcações')} em {plural(files, 'arquivo', 'arquivos')} ({counts})."


def render_table(
    items: Sequence[Item],
    now: float,
    group_by: Optional[str] = None,
    tags: Sequence[str] = DEFAULT_TAGS,
    width: Optional[int] = None,
    color: bool = False,
) -> str:
    if not items:
        return summary_line(items) + "\n"

    def cells(i: Item) -> Tuple[str, ...]:
        return (f"{i.path}:{i.line}", tag_label(i), author_label(i)[:24], format_age(age_days(i, now)), i.text)

    header = ("LOCAL", "TAG", "AUTOR", "IDADE", "TEXTO")
    rows = [cells(i) for i in items]
    widths = [max(len(header[c]), *(len(r[c]) for r in rows)) for c in range(4)]
    fixed = sum(widths) + 2 * 4

    def line(row: Tuple[str, ...], tag: Optional[str] = None) -> str:
        parts = [row[c].ljust(widths[c]) for c in range(4)]
        if color and tag:
            parts[1] = f"\033[{TAG_COLORS.get(tag, '1')}m{parts[1]}\033[0m"
        text = row[4]
        if width and fixed + len(text) > width:
            text = text[: max(10, width - fixed - 3)] + "..."
        return ("  ".join(parts) + "  " + text).rstrip()

    out = [line(header)]
    if group_by:
        for name, group in group_items(items, group_by, tags):
            out += ["", f"{name} ({len(group)})"] + [line(cells(i), i.tag) for i in group]
    else:
        out += [line(cells(i), i.tag) for i in items]
    out += ["", summary_line(items)]
    return "\n".join(out) + "\n"


def _md(text: str) -> str:
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def render_markdown(items: Sequence[Item], now: float, group_by: Optional[str] = None,
                    tags: Sequence[str] = DEFAULT_TAGS) -> str:
    def table(group: Sequence[Item]) -> List[str]:
        lines = ["| Local | Tag | Autor | Idade | Texto |", "|---|---|---|---|---|"]
        for i in group:
            lines.append(
                f"| `{i.path}:{i.line}` | {_md(tag_label(i))} | {_md(author_label(i))} "
                f"| {format_age(age_days(i, now))} | {_md(i.text)} |"
            )
        return lines

    out: List[str] = []
    if items and group_by:
        for name, group in group_items(items, group_by, tags):
            out += [f"### {_md(name)} ({len(group)})", ""] + table(group) + [""]
    elif items:
        out += table(items) + [""]
    out.append(summary_line(items))
    return "\n".join(out) + "\n"


def _item_dict(item: Item, now: float) -> dict:
    days = age_days(item, now)
    when = datetime.fromtimestamp(item.timestamp).astimezone().isoformat(timespec="seconds") if item.timestamp else None
    return {
        "arquivo": item.path,
        "linha": item.line,
        "tag": item.tag,
        "responsavel": item.owner or None,
        "texto": item.text,
        "autor": item.author,
        "data": when,
        "idade_dias": int(days) if days is not None else None,
        "idade": format_age(days),
        "origem": item.source,
    }


def render_json(items: Sequence[Item], now: float, group_by: Optional[str] = None,
                tags: Sequence[str] = DEFAULT_TAGS) -> str:
    data: dict = {"total": len(items), "por_tag": dict(Counter(i.tag for i in items).most_common())}
    if group_by:
        data["agrupado_por"] = group_by
        data["grupos"] = [
            {"nome": name, "total": len(group), "itens": [_item_dict(i, now) for i in group]}
            for name, group in group_items(items, group_by, tags)
        ]
    else:
        data["itens"] = [_item_dict(i, now) for i in items]
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"
