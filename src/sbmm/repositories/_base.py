"""Utilitários comuns aos repositórios."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from sbmm.domain.errors import DataAccessError

log = logging.getLogger(__name__)
T = TypeVar("T")


def validate_id(value: Any, name: str = "anchor_player_id") -> int:
    """Aceita apenas inteiros positivos (bool não conta como int aqui)."""
    if isinstance(value, bool):
        raise ValueError(f"{name} inválido: {value!r}")
    try:
        ivalue = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} inválido: {value!r}") from exc
    if ivalue <= 0 or ivalue != value:
        raise ValueError(f"{name} deve ser um inteiro positivo: {value!r}")
    return ivalue


def run_query(operation: str, fn: Callable[[], T]) -> T:
    """Executa uma chamada ao Supabase convertendo qualquer falha em ``DataAccessError``."""
    try:
        return fn()
    except DataAccessError:
        raise
    except Exception as exc:  # noqa: BLE001 - client do Supabase lança vários tipos
        log.exception("Falha em %s", operation)
        raise DataAccessError(f"Falha ao executar {operation}: {exc}", operation=operation) from exc

