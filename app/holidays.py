"""Feriados nacionais portugueses (incluindo os móveis, calculados a partir da Páscoa)."""

from datetime import date, timedelta
from functools import lru_cache

from flask import current_app, has_app_context


def easter(year):
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


@lru_cache(maxsize=64)
def _national_holidays(year):
    e = easter(year)
    return {
        date(year, 1, 1): "Ano Novo",
        e - timedelta(days=2): "Sexta-feira Santa",
        e: "Páscoa",
        date(year, 4, 25): "Dia da Liberdade",
        date(year, 5, 1): "Dia do Trabalhador",
        e + timedelta(days=60): "Corpo de Deus",
        date(year, 6, 10): "Dia de Portugal",
        date(year, 8, 15): "Assunção de Nossa Senhora",
        date(year, 10, 5): "Implantação da República",
        date(year, 11, 1): "Dia de Todos os Santos",
        date(year, 12, 1): "Restauração da Independência",
        date(year, 12, 8): "Imaculada Conceição",
        date(year, 12, 25): "Natal",
    }


def holidays(year):
    result = dict(_national_holidays(year))
    extra = current_app.config.get("EXTRA_HOLIDAYS", "") if has_app_context() else ""
    for item in filter(None, (s.strip() for s in extra.split(","))):
        try:
            month, day = (int(x) for x in item.split("-"))
            result.setdefault(date(year, month, day), "Feriado local")
        except ValueError:
            continue
    return result


def is_working_day(d):
    return d.weekday() < 5 and d not in holidays(d.year)
