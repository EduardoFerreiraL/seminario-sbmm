"""Chamadas às funções RPC do PostgreSQL (``matchmake_in_db``, ``matchmake_explain``, ``explain_knn``)."""

from __future__ import annotations

from typing import Any

from supabase import Client

from sbmm.domain.matchmaking import plan_lines
from sbmm.repositories._base import run_query, validate_id


class MatchmakingRepository:
    def __init__(self, client: Client) -> None:
        self._db = client

    def run_matchmaking(self, anchor_id: int) -> list[dict[str, Any]]:
        """KNN + Snake Draft + Regressão Logística, tudo dentro do SGBD."""
        aid = validate_id(anchor_id)
        res = run_query(
            "matchmake_in_db",
            lambda: self._db.rpc("matchmake_in_db", {"anchor_player_id": aid}).execute(),
        )
        return list(res.data or [])

    def explain_regression(self, anchor_id: int) -> dict[str, Any] | None:
        """Intermediários da regressão calculados no SGBD (None se não houver linha)."""
        aid = validate_id(anchor_id)
        res = run_query(
            "matchmake_explain",
            lambda: self._db.rpc("matchmake_explain", {"anchor_player_id": aid}).execute(),
        )
        return res.data[0] if res.data else None

    def explain_knn(self, anchor_id: int, *, force_index: bool = False) -> list[str]:
        """Plano de execução (EXPLAIN ANALYZE) da busca KNN."""
        aid = validate_id(anchor_id)
        res = run_query(
            "explain_knn",
            lambda: self._db.rpc("explain_knn", {"anchor_player_id": aid, "force_index": bool(force_index)}).execute(),
        )
        return plan_lines(res.data)

