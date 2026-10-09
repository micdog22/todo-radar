"""Permite rodar com `python -m todo_radar`."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
