"""Etapa 3: divisão dos times por Snake Draft ABBA."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from sbmm.config.constants import MATCH_SIZE, SNAKE_T1_RANKS, TEAM_AZUL, TEAM_VERM
from sbmm.views.sql_snippets import SQL_SNAKE


def render(df_snake: pd.DataFrame) -> None:
    st.markdown(
        "**💡 O que acontece:** os 10 vizinhos são ordenados por MMR (do maior para o menor) e distribuídos em "
        "**zigue-zague** (Snake Draft ABBA). Assim, o melhor jogador fica no Time 1, mas o Time 2 recebe o 2º e o 3º, "
        "e assim por diante, o que equilibra a soma de MMR."
    )
    padrao = " ".join("🔵" if r in SNAKE_T1_RANKS else "🔴" for r in range(1, MATCH_SIZE + 1))
    st.markdown(f"**Padrão de escolha (posição 1 → 10):** {padrao}")

    show = df_snake[["rk", "assigned_team", "summoner_name", "mmr"]].copy()
    show["Escolha"] = show["rk"].apply(lambda r: "A" if r in SNAKE_T1_RANKS else "B")
    st.dataframe(
        show[["rk", "Escolha", "assigned_team", "summoner_name", "mmr"]],
        hide_index=True,
        column_config={
            "rk": st.column_config.NumberColumn("Posição (rk)"),
            "assigned_team": "Time",
            "summoner_name": "Invocador",
            "mmr": st.column_config.NumberColumn("MMR", format="%.1f"),
        },
    )
    s1 = df_snake.loc[df_snake["assigned_team"] == TEAM_AZUL, "mmr"].sum()
    s2 = df_snake.loc[df_snake["assigned_team"] == TEAM_VERM, "mmr"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Σ MMR 🔵 Time 1", f"{s1:.1f}")
    c2.metric("Σ MMR 🔴 Time 2", f"{s2:.1f}")
    c3.metric("Diferença", f"{abs(s1 - s2):.1f}")
    st.markdown("**🧾 Trecho SQL responsável:**")
    st.code(SQL_SNAKE, language="sql")

