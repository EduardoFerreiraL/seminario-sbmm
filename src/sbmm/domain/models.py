"""Entidades tipadas que trafegam entre as camadas (substituem os dicts soltos)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from typing import Any

import pandas as pd

_INDEX_SCAN_ON_QUEUE = re.compile(r"Index Scan using \S+ on players_mmr p\b")


@dataclass(frozen=True)
class ModelWeights:
    """Pesos da regressão logística (tabela ml_model_weights)."""

    model_name: str
    intercept: float
    w_mmr_diff: float
    w_wr_diff: float
    w_agg_diff: float

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> ModelWeights:
        return cls(
            model_name=str(row["model_name"]),
            intercept=float(row["intercept"]),
            w_mmr_diff=float(row["w_mmr_diff"]),
            w_wr_diff=float(row["w_wr_diff"]),
            w_agg_diff=float(row["w_agg_diff"]),
        )


@dataclass(frozen=True)
class RegressionExplain:
    """Todos os termos intermediários da fórmula z = β0 + Σ w·Δ e P = sigmoide(z)."""

    model_name: str
    t1_mmr: float
    t2_mmr: float
    d_mmr: float
    t1_wr: float
    t2_wr: float
    d_wr: float
    t1_agg: float
    t2_agg: float
    d_agg: float
    intercept: float
    w_mmr_diff: float
    w_wr_diff: float
    w_agg_diff: float
    contrib_mmr: float
    contrib_wr: float
    contrib_agg: float
    z: float
    prob_pct: float

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> RegressionExplain:
        """Converte a linha devolvida por ``matchmake_explain`` (valores NUMERIC chegam como str/Decimal)."""
        values: dict[str, Any] = {}
        for f in fields(cls):
            v = row.get(f.name)
            if f.name == "model_name":
                values[f.name] = str(v)
            elif v is None:
                raise ValueError(f"matchmake_explain devolveu {f.name} = NULL")
            else:
                values[f.name] = float(v)
        return cls(**values)


@dataclass(frozen=True)
class ExecutionPlan:
    """Plano de execução (EXPLAIN ANALYZE) da busca KNN."""

    lines: list[str] = field(default_factory=list)
    forced_lines: list[str] | None = None
    error: str | None = None

    @property
    def available(self) -> bool:
        return self.error is None

    @property
    def used_index(self) -> bool:
        return uses_queue_index(self.lines)


def uses_queue_index(plan: list[str] | None) -> bool:
    """True se a varredura da FILA (alias ``p``) foi feita por índice.

    A linha do âncora (alias ``a``) usa a chave primária e não conta.
    """
    return any(_INDEX_SCAN_ON_QUEUE.search(ln) for ln in plan or [])


@dataclass(frozen=True)
class MatchResult:
    """Partida formada pela RPC ``matchmake_in_db``."""

    anchor_id: int
    players: pd.DataFrame
    win_prob: float
    latency_ms: float

    @property
    def max_distance(self) -> float:
        return float(self.players["vector_distance"].max())


@dataclass(frozen=True)
class Explanation:
    """Dados usados pela aba "Como o SGBD chegou aqui"."""

    snake: pd.DataFrame
    regression: RegressionExplain | None
    regression_from_db: bool
    plan: ExecutionPlan


@dataclass(frozen=True)
class ConsistencyReport:
    """Conferências automáticas entre a explicação e o resultado da RPC."""

    teams_match: bool
    formula_prob: float
    formula_matches: bool
    explain_matches: bool

    @property
    def all_ok(self) -> bool:
        return self.teams_match and self.formula_matches and self.explain_matches

