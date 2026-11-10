"""Etapa 2: busca KNN no índice HNSW + plano de execução real."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from sbmm.domain.models import ExecutionPlan
from sbmm.views.charts import vector_space_chart
from sbmm.views.sql_snippets import SQL_KNN


def render(df_players: pd.DataFrame, df_match: pd.DataFrame, anchor_row: pd.Series, plan: ExecutionPlan) -> None:
    st.markdown(
        "**💡 O que acontece:** o operador `<->` do pgvector calcula a **distância Euclidiana** entre o vetor do "
        "âncora e o de cada jogador da fila. O `ORDER BY ... LIMIT 10` devolve os 10 mais próximos, e o "
        "**índice HNSW** (um grafo de navegação) encontra esses vizinhos **sem comparar com a fila inteira**."
    )
    st.latex(r"d(a,b) = \sqrt{\sum_{i=1}^{4} (a_i - b_i)^2}")

    st.markdown(f"**📊 Onde estão os 10 vizinhos dentro da fila ({len(df_players)} jogadores):**")
    st.altair_chart(vector_space_chart(df_players, df_match, int(anchor_row["player_id"])), width="stretch")
    st.caption(
        "Projeção 2D (MMR × Winrate) de um espaço que, na verdade, tem 4 dimensões. Um ponto que parece "
        "distante aqui pode estar próximo em **agressividade** e **duração média**, e vice-versa."
    )

    viz = df_match.sort_values("vector_distance")[["summoner_name", "assigned_team", "mmr", "winrate", "vector_distance"]]
    st.dataframe(
        viz,
        hide_index=True,
        column_config={
            "summoner_name": "Invocador",
            "assigned_team": "Time atribuído",
            "mmr": st.column_config.NumberColumn("MMR", format="%.1f"),
            "winrate": st.column_config.NumberColumn("Winrate (%)", format="%.2f"),
            "vector_distance": st.column_config.ProgressColumn(
                "Distância ao âncora", format="%.4f", min_value=0.0, max_value=float(max(viz["vector_distance"].max(), 1e-9))
            ),
        },
    )

    st.markdown("**🧾 Trecho SQL responsável:**")
    st.code(SQL_KNN, language="sql")
    _render_plan(plan, len(df_players))


def _render_plan(plan: ExecutionPlan, queue_size: int) -> None:
    st.markdown("**🔬 Prova técnica: plano de execução real do PostgreSQL (`EXPLAIN ANALYZE`)**")
    if not plan.available:
        st.warning(
            "A função `explain_knn` ainda não existe no banco (ou falhou). Rode o arquivo "
            "`sql/migrations/002_functions.sql` no SQL Editor do Supabase para habilitar esta prova."
        )
        return
    if plan.used_index:
        st.success("✅ O otimizador escolheu **Index Scan** no índice HNSW para encontrar os vizinhos.")
        st.code("\n".join(plan.lines), language="text")
        return
    st.info(
        f"Com apenas {queue_size} jogadores, o otimizador do PostgreSQL considerou a **varredura sequencial** "
        "(Seq Scan) mais barata que o índice. Isso é esperado em tabelas pequenas: o HNSW compensa em "
        "filas grandes (milhares a milhões de jogadores)."
    )
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Plano escolhido livremente pelo otimizador:")
        st.code("\n".join(plan.lines), language="text")
    with c2:
        st.caption("Mesmo SQL com `enable_seqscan = off` (força o índice):")
        st.code("\n".join(plan.forced_lines or ["(sem retorno)"]), language="text")

