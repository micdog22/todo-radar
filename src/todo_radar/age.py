"""Idades: leitura de "90d", "6m", "1a" e exibição como "há 3 meses"."""

from __future__ import annotations

import re
from typing import Optional

UNITS = {"d": 1, "s": 7, "m": 30, "a": 365}


def parse_age(text: str) -> int:
    """Converte 90d, 2s, 6m ou 1a (dias, semanas, meses, anos) em dias."""
    match = re.fullmatch(r"\s*(\d+)\s*([dsmaDSMA])\s*", text or "")
    if not match:
        raise ValueError(
            f"idade inválida: {text!r} (use um número com d, s, m ou a, como 90d, 2s, 6m ou 1a)"
        )
    return int(match.group(1)) * UNITS[match.group(2).lower()]


def format_age(days: Optional[float]) -> str:
    if days is None:
        return "sem data"
    days = int(days)
    if days < 1:
        return "hoje"
    if days == 1:
        return "ontem"
    if days < 7:
        return f"há {days} dias"
    if days < 30:
        weeks = days // 7
        return "há 1 semana" if weeks == 1 else f"há {weeks} semanas"
    if days < 365:
        months = days // 30
        return "há 1 mês" if months == 1 else f"há {months} meses"
    years = days // 365
    return "há 1 ano" if years == 1 else f"há {years} anos"
