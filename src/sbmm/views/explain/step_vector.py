"""Etapa 1: vetorização do jogador âncora."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from sbmm.domain.vectorization import NORMALIZATION_FORMULAS, VECTOR_DIMENSIONS
from sbmm.views.sql_snippets import SQL_VETOR


def render(anchor_row: pd.Series) -> None:
    st.markdown(
        "**💡 O que acontece:** cada jogador é representado como um **ponto num espaço de 4 dimensões**. "
        "Os valores são normalizados entre 0 e 1 para que nenhuma métrica domine a distância "
        "(sem isso, o MMR, que vai até 2600, pesaria muito mais que o winrate)."
    )
    vec = anchor_row["skill_vector"] or [None] * 4
    df_vec = pd.DataFrame(
        {
            "Dimensão": list(VECTOR_DIMENSIONS),
            "Valor bruto": [
                anchor_row["mmr"], anchor_row["winrate"], anchor_row["aggression_score"], anchor_row["avg_game_duration"]
            ],
            "Normalização": list(NORMALIZATION_FORMULAS),
            "Valor no vetor (SGBD)": vec,
        }
    )
    st.markdown(f"**📊 Vetor do jogador âncora `{anchor_row['summoner_name']}`:**")
    st.dataframe(
        df_vec,
        hide_index=True,
        column_config={
            "Valor bruto": st.column_config.NumberColumn(format="%.2f"),
            "Valor no vetor (SGBD)": st.column_config.ProgressColumn(format="%.4f", min_value=0.0, max_value=1.0),
        },
    )
    st.code(f"skill_vector = {json.dumps(vec)}", language="sql")
    st.markdown("**🧾 Estrutura no banco:**")
    st.code(SQL_VETOR, language="sql")

