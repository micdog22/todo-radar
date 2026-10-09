"""Linha de comando do todo-radar."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path
from typing import List, Optional

from . import __version__
from .age import parse_age
from .argparse_ptbr import ArgumentParser
from .extract import DEFAULT_TAGS, parse_tags
from .report import filter_older_than, render_json, render_markdown, render_table, sort_items
from .scanner import scan

PROG = "todo-radar"

EPILOG = """\
exemplos:
  todo-radar                              varre a pasta atual
  todo-radar ~/projetos/loja --agrupar autor
  todo-radar --mais-velho-que 6m          só o que está esquecido há 6 meses ou mais
  todo-radar --tags TODO,FIXME --markdown > TODOS.md
  todo-radar --mais-velho-que 1a --falhar-se-encontrar   (para CI)

idades: d = dias, s = semanas, m = meses (30 dias), a = anos (365 dias).
códigos de saída: 0 ok, 1 marcações encontradas com --falhar-se-encontrar, 2 uso incorreto.
"""


def _age(text: str) -> int:
    try:
        return parse_age(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def build_parser() -> argparse.ArgumentParser:
    parser = ArgumentParser(
        prog=PROG,
        description=(
            "Encontra TODOs, FIXMEs e outras marcações esquecidas nos comentários do código\n"
            "e mostra quem escreveu e há quanto tempo (pelo git blame)."
        ),
        epilog=EPILOG,
    )
    parser.add_argument("pasta", nargs="?", default=".", help="pasta do projeto (padrão: a pasta atual)")
    parser.add_argument("--tags", metavar="LISTA",
                        help=f"marcações procuradas, separadas por vírgula (padrão: {','.join(DEFAULT_TAGS)})")
    parser.add_argument("--agrupar", choices=("arquivo", "tag", "autor"), help="agrupa o resultado")
    formats = parser.add_mutually_exclusive_group()
    formats.add_argument("--markdown", action="store_true", help="tabela em Markdown (para issues, PRs e wikis)")
    formats.add_argument("--json", action="store_true", help="resultado em JSON")
    parser.add_argument("--mais-velho-que", type=_age, metavar="IDADE",
                        help="só marcações mais antigas que IDADE, como 90d, 2s, 6m ou 1a")
    parser.add_argument("--falhar-se-encontrar", action="store_true", help="sai com código 1 se encontrar alguma marcação (para CI)")
    parser.add_argument("--sem-git", action="store_true", help="não usa o git: varre as pastas e usa a data dos arquivos")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}", help="mostra a versão e sai")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    folder = Path(args.pasta).expanduser()
    if not folder.is_dir():
        parser.error(f"pasta não encontrada: {args.pasta}")
    try:
        tags = parse_tags(args.tags)
    except ValueError as exc:
        parser.error(str(exc))

    result = scan(folder, tags, use_git=not args.sem_git)
    now = time.time()
    items = result.items
    if args.mais_velho_que is not None:
        items = filter_older_than(items, args.mais_velho_que, now)
    items = sort_items(items)

    if args.json:
        output = render_json(items, now, args.agrupar, tags)
    elif args.markdown:
        output = render_markdown(items, now, args.agrupar, tags)
    else:
        tty = sys.stdout.isatty()
        width = shutil.get_terminal_size().columns if tty else None
        output = render_table(items, now, args.agrupar, tags, width=width, color=tty and not os.environ.get("NO_COLOR"))
        if not result.used_git and items:
            output += "Sem git: a idade é estimada pela data de modificação dos arquivos.\n"
    sys.stdout.write(output)
    return 1 if args.falhar_se_encontrar and items else 0
