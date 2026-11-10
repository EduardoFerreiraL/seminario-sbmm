"""Regras do matchmaking reproduzidas em Python (para validação e fallback do SQL)."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

import pandas as pd

from sbmm.config.constants import SNAKE_T1_RANKS, TEAM_AZUL, TEAM_VERM
from sbmm.domain.errors import MatchmakingError
from sbmm.domain.models import ConsistencyReport, ModelWeights, RegressionExplain

_PROB_TOLERANCE = 0.011  # 2 casas decimais (ROUND no SQL)


def sigmoid_pct(z: float) -> float:
    """Função logística em porcentagem (0-100), numericamente estável."""
    if z >= 0:
        return 100.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return 100.0 * ez / (1.0 + ez)


def team_for_rank(rank: int) -> str:
    """Snake Draft ABBA: posições 1,4,5,8,9 vão para o Time 1."""
    return TEAM_AZUL if rank in SNAKE_T1_RANKS else TEAM_VERM


def to_numeric(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Converte colunas NUMERIC (que chegam como texto pelo PostgREST) para float."""
    out = df.copy()
    for c in columns:
        if c in out:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def snake_ranking(df_match: pd.DataFrame) -> pd.DataFrame:
    """Reconstrói o ``ROW_NUMBER() OVER (ORDER BY mmr DESC, player_id)`` + CASE do SQL."""
    d = df_match.sort_values(["mmr", "player_id"], ascending=[False, True]).reset_index(drop=True)
    d["rk"] = d.index + 1
    d["time_recalculado"] = d["rk"].apply(team_for_rank)
    return d


def validate_match(df_match: pd.DataFrame) -> float:
    """Garante que a RPC formou dois times e devolveu probabilidade. Retorna a probabilidade.

    A RPC pode devolver ``predicted_team1_win_prob = NULL`` quando um dos times fica
    vazio (média de 0 linhas = NULL no SQL).
    """
    if df_match.empty or "assigned_team" not in df_match:
        raise MatchmakingError("A função matchmake_in_db não retornou jogadores.", raw=df_match)

    n_t1 = int((df_match["assigned_team"] == TEAM_AZUL).sum())
    n_t2 = int((df_match["assigned_team"] == TEAM_VERM).sum())
    probs = (
        pd.to_numeric(df_match["predicted_team1_win_prob"], errors="coerce").dropna()
        if "predicted_team1_win_prob" in df_match
        else pd.Series(dtype=float)
    )
    if probs.empty or n_t1 == 0 or n_t2 == 0:
        raise MatchmakingError(
            "A função matchmake_in_db não conseguiu formar dois times para este jogador "
            f"(Time 1: {n_t1} jogadores | Time 2: {n_t2} jogadores), "
            "então a probabilidade de vitória veio NULL.",
            n_team1=n_t1,
            n_team2=n_t2,
            raw=df_match,
        )
    return float(probs.iloc[0])


def compute_regression_explain(df_match: pd.DataFrame, w: ModelWeights) -> RegressionExplain:
    """Fallback (se ``matchmake_explain`` não existir): mesmos cálculos do SQL, feitos no Python."""
    t1 = df_match[df_match["assigned_team"] == TEAM_AZUL]
    t2 = df_match[df_match["assigned_team"] == TEAM_VERM]
    t1_mmr, t2_mmr = float(t1["mmr"].mean()), float(t2["mmr"].mean())
    t1_wr, t2_wr = float(t1["winrate"].mean()), float(t2["winrate"].mean())
    t1_agg, t2_agg = float(t1["aggression_score"].mean()), float(t2["aggression_score"].mean())
    d_mmr, d_wr, d_agg = t1_mmr - t2_mmr, t1_wr - t2_wr, t1_agg - t2_agg
    c_mmr, c_wr, c_agg = w.w_mmr_diff * d_mmr, w.w_wr_diff * d_wr, w.w_agg_diff * d_agg
    z = w.intercept + c_mmr + c_wr + c_agg
    return RegressionExplain(
        model_name=w.model_name,
        t1_mmr=t1_mmr, t2_mmr=t2_mmr, d_mmr=d_mmr,
        t1_wr=t1_wr, t2_wr=t2_wr, d_wr=d_wr,
        t1_agg=t1_agg, t2_agg=t2_agg, d_agg=d_agg,
        intercept=w.intercept, w_mmr_diff=w.w_mmr_diff, w_wr_diff=w.w_wr_diff, w_agg_diff=w.w_agg_diff,
        contrib_mmr=c_mmr, contrib_wr=c_wr, contrib_agg=c_agg,
        z=z,
        prob_pct=round(sigmoid_pct(z), 2),
    )


def check_consistency(df_snake: pd.DataFrame, e: RegressionExplain, win_prob: float) -> ConsistencyReport:
    """Compara times recalculados, sigmoide e intermediários com o resultado da RPC."""
    p_formula = sigmoid_pct(e.z)
    return ConsistencyReport(
        teams_match=bool((df_snake["time_recalculado"] == df_snake["assigned_team"]).all()),
        formula_prob=p_formula,
        formula_matches=abs(round(p_formula, 2) - win_prob) < _PROB_TOLERANCE,
        explain_matches=abs(e.prob_pct - win_prob) < _PROB_TOLERANCE,
    )


def plan_lines(data: Any) -> list[str]:
    """``RETURNS SETOF TEXT`` pode vir como lista de strings ou lista de dicts."""
    lines: list[str] = []
    for item in data or []:
        lines.append(str(next(iter(item.values()))) if isinstance(item, dict) else str(item))
    return lines

