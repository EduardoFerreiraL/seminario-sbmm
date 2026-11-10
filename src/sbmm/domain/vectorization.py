"""Vetorização 4D dos jogadores (mesma normalização usada para gerar ``skill_vector``)."""

from __future__ import annotations

import json
from typing import Any

from sbmm.config.constants import AGG_MAX, DUR_MAX_MIN, MMR_MAX, MMR_MIN, WR_MAX, WR_MIN

VECTOR_DIMENSIONS = ("MMR", "Winrate (%)", "Agressividade", "Duração média (min)")
NORMALIZATION_FORMULAS = (
    f"(mmr − {MMR_MIN:.0f}) / {MMR_MAX - MMR_MIN:.0f}",
    f"(wr − {WR_MIN:.0f}) / {WR_MAX - WR_MIN:.0f}",
    f"agg / {AGG_MAX:.0f}",
    f"min(dur / {DUR_MAX_MIN:.0f}, 1)",
)


def normalize_player(mmr: float, winrate: float, aggression: float, duration_min: float) -> list[float]:
    """Normaliza as 4 métricas em [0, 1] para que nenhuma domine a distância Euclidiana."""
    return [
        round((mmr - MMR_MIN) / (MMR_MAX - MMR_MIN), 4),
        round((winrate - WR_MIN) / (WR_MAX - WR_MIN), 4),
        round(aggression / AGG_MAX, 4),
        round(min(duration_min / DUR_MAX_MIN, 1.0), 4),
    ]


def parse_vector(v: Any) -> list[float] | None:
    """pgvector chega via PostgREST como texto ``'[0.1,0.2,...]'``."""
    if v is None:
        return None
    if isinstance(v, str):
        return [float(x) for x in json.loads(v)]
    return [float(x) for x in v]

