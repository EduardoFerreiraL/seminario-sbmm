"""Acesso à tabela ``players_mmr``."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pandas as pd
from supabase import Client

from sbmm.config.constants import PLAYER_NUMERIC_COLS
from sbmm.domain.matchmaking import to_numeric
from sbmm.domain.vectorization import parse_vector
from sbmm.repositories._base import run_query

TABLE = "players_mmr"
QUEUE_COLUMNS = (
    "player_id, summoner_name, main_role, mmr, winrate, aggression_score, avg_game_duration, skill_vector"
)


class PlayerRepository:
    def __init__(self, client: Client) -> None:
        self._db = client

    def list_queue(self) -> pd.DataFrame:
        """Jogadores com ``in_queue = TRUE``, ordenados por MMR (desc)."""
        res = run_query(
            "listar fila (players_mmr)",
            lambda: self._db.table(TABLE).select(QUEUE_COLUMNS).eq("in_queue", True).order("mmr", desc=True).execute(),
        )
        df = pd.DataFrame(res.data or [])
        if df.empty:
            return df
        df["skill_vector"] = df["skill_vector"].apply(parse_vector)
        return to_numeric(df, PLAYER_NUMERIC_COLS)

    def ping(self) -> None:
        """Consulta mínima para validar conexão e permissão de leitura."""
        run_query("testar conexão", lambda: self._db.table(TABLE).select("player_id").limit(1).execute())

    def upsert_many(self, players: Sequence[dict[str, Any]], batch_size: int = 250) -> None:
        """Escrita em lotes. Requer a chave de serviço (RLS bloqueia a chave pública)."""
        for i in range(0, len(players), batch_size):
            batch = list(players[i : i + batch_size])
            run_query("gravar jogadores", lambda b=batch: self._db.table(TABLE).upsert(b).execute())

