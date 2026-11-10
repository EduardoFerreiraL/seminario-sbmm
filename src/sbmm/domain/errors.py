"""Exceções do projeto. Permitem à camada de UI exibir mensagens amigáveis por tipo de erro."""

from __future__ import annotations

from typing import Any


class SbmmError(Exception):
    """Erro base do projeto."""


class ConfigError(SbmmError):
    """Configuração ausente ou inválida (.env)."""


class DataAccessError(SbmmError):
    """Falha ao consultar o Supabase (rede, permissão, função inexistente...)."""

    def __init__(self, message: str, *, operation: str) -> None:
        super().__init__(message)
        self.operation = operation


class MatchmakingError(SbmmError):
    """A RPC respondeu, mas o resultado não forma uma partida válida."""

    def __init__(self, message: str, *, n_team1: int = 0, n_team2: int = 0, raw: Any = None) -> None:
        super().__init__(message)
        self.n_team1 = n_team1
        self.n_team2 = n_team2
        self.raw = raw

