"""Acesso à tabela ``ml_model_weights`` e ao histórico ``lol_matches_history``."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from supabase import Client

from sbmm.config.constants import MODEL_NAME
from sbmm.domain.models import ModelWeights
from sbmm.repositories._base import run_query


class ModelRepository:
    def __init__(self, client: Client) -> None:
        self._db = client

    def get_weights(self, model_name: str = MODEL_NAME) -> ModelWeights | None:
        res = run_query(
            "ler pesos do modelo",
            lambda: self._db.table("ml_model_weights").select("*").eq("model_name", model_name).execute(),
        )
        return ModelWeights.from_mapping(res.data[0]) if res.data else None

    def upsert_match_history(self, matches: Sequence[dict[str, Any]], batch_size: int = 250) -> None:
        """Grava o histórico de partidas (dataset do Kaggle). Requer a chave de serviço."""
        for i in range(0, len(matches), batch_size):
            batch = list(matches[i : i + batch_size])
            run_query(
                "gravar histórico de partidas",
                lambda b=batch: self._db.table("lol_matches_history").upsert(b).execute(),
            )

