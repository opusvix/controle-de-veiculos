"""Formatação e interpretação de números, datas e valores no padrão pt-BR."""
from __future__ import annotations

import datetime as dt

DATE_INPUT = "%d/%m/%Y"
_ISO = "%Y-%m-%d"


def fmt_number(value: float | int | None, decimals: int = 2) -> str:
    """Formata um número no padrão brasileiro: 1234.5 -> '1.234,50'."""
    if value is None:
        return "-"
    return f"{value:,.{decimals}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def fmt_brl(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "-"
    return "R$ " + fmt_number(value, decimals)


def parse_number(text: str | None) -> float | None:
    """Interpreta números digitados no padrão brasileiro ou americano.

    Aceita '1.234,56', '1234,56', '1234.56', '45.123'. Retorna None se inválido.
    """
    if not text:
        return None
    t = "".join(ch for ch in str(text) if ch.isdigit() or ch in ".,-")
    if not t.strip(",.-"):
        return None
    negative = "-" in t
    t = t.replace("-", "")
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    else:
        parts = t.split(".")
        if len(parts) > 2:
            # Milhar com vários pontos: 1.234.567
            t = "".join(parts[:-1]) + "." + parts[-1]
        elif len(parts) == 2 and len(parts[1]) == 3 and len(t) > 4:
            # Ponto de milhar: 45.123 (2 pontos decimais como 5.79 continuam decimais)
            t = "".join(parts)
    try:
        value = float(t)
    except ValueError:
        return None
    return -value if negative else value


def today_input() -> str:
    return dt.date.today().strftime(DATE_INPUT)


def today_iso() -> str:
    return dt.date.today().isoformat()


def parse_date(text: str | None) -> dt.date | None:
    if not text:
        return None
    t = str(text).strip()
    for fmt in (DATE_INPUT, _ISO, "%d-%m-%Y", "%d/%m/%y"):
        try:
            return dt.datetime.strptime(t, fmt).date()
        except ValueError:
            continue
    return None


def fmt_date(iso: str | None) -> str:
    if not iso:
        return "-"
    try:
        return dt.date.fromisoformat(iso).strftime(DATE_INPUT)
    except ValueError:
        return iso


def month_label(iso: str) -> str:
    """'2026-09' -> '09/2026'."""
    year, month = iso.split("-")[:2]
    return f"{month}/{year}"
