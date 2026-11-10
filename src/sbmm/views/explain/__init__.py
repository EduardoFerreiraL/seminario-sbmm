"""Aba "Como o SGBD chegou aqui": uma view por etapa do pipeline."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from sbmm.domain.models import Explanation, MatchResult
from sbmm.views import sql_snippets
from sbmm.views.explain import consistency, pipeline, step_knn, step_regression, step_snake, step_vector


def render(df_players: pd.DataFrame, anchor_row: pd.Series, match: MatchResult, expl: Explanation) -> None:
    pipeline.render(match.latency_ms)

    with st.expander("**Etapa 1 · Vetorização do jogador (pgvector)**"):
        step_vector.render(anchor_row)
    with st.expander("**Etapa 2 · Busca dos 10 vizinhos mais próximos (KNN + índice HNSW)**"):
        step_knn.render(df_players, match.players, anchor_row, expl.plan)
    with st.expander("**Etapa 3 · Divisão dos times (Snake Draft ABBA)**"):
        step_snake.render(expl.snake)
    with st.expander("**Etapa 4 · Probabilidade de vitória (Regressão Logística em SQL)**"):
        if expl.regression:
            step_regression.render(expl.regression, expl.regression_from_db)
        else:
            st.error("Não foi possível obter os pesos do modelo (`ml_model_weights`).")

    if expl.regression:
        consistency.render(expl.snake, expl.regression, match.win_prob, expl.regression_from_db)

    with st.expander("🔍 Ver chamadas SQL executadas pelo SGBD"):
        st.code(sql_snippets.executed_calls(match.anchor_id), language="sql")

