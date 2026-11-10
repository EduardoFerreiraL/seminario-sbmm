"""Etapa 4: regressão logística calculada no SGBD."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from sbmm.domain.models import RegressionExplain
from sbmm.views.charts import sigmoid_chart
from sbmm.views.sql_snippets import SQL_REGRESSAO


def render(e: RegressionExplain, origem_sgbd: bool) -> None:
    st.markdown(
        "**💡 O que acontece:** o banco calcula as **médias** de cada time e as **diferenças** entre elas (Δ). "
        "Cada Δ é multiplicado por um **peso** treinado (tabela `ml_model_weights`), a soma vira o valor **z**, "
        "e a função **sigmoide** transforma z numa probabilidade entre 0% e 100%."
    )
    if origem_sgbd:
        st.caption("✅ Todos os números abaixo foram calculados **pelo PostgreSQL** (função `matchmake_explain`).")
    else:
        st.warning(
            "A função `matchmake_explain` ainda não existe no banco, então os números abaixo foram recalculados "
            "no Python com os pesos do banco. Rode `sql/migrations/002_functions.sql` no Supabase para que eles "
            "venham do SGBD."
        )

    tabela = pd.DataFrame(
        {
            "Feature": ["MMR médio", "Winrate médio (%)", "Agressividade média"],
            "🔵 Time 1": [e.t1_mmr, e.t1_wr, e.t1_agg],
            "🔴 Time 2": [e.t2_mmr, e.t2_wr, e.t2_agg],
            "Δ (T1 − T2)": [e.d_mmr, e.d_wr, e.d_agg],
            "Peso (w)": [e.w_mmr_diff, e.w_wr_diff, e.w_agg_diff],
            "Contribuição (w·Δ)": [e.contrib_mmr, e.contrib_wr, e.contrib_agg],
        }
    )
    st.markdown(f"**📊 Entradas do modelo `{e.model_name}`:**")
    st.dataframe(
        tabela,
        hide_index=True,
        column_config={c: st.column_config.NumberColumn(format="%.4f") for c in tabela.columns[1:]},
    )

    st.markdown("**Fórmula com os valores desta partida:**")
    st.latex(r"z = \beta_0 + w_{mmr}\,\Delta_{mmr} + w_{wr}\,\Delta_{wr} + w_{agg}\,\Delta_{agg}")
    st.latex(
        rf"z = {e.intercept:.3f} + ({e.w_mmr_diff:.3f})({e.d_mmr:.2f}) + ({e.w_wr_diff:.3f})({e.d_wr:.2f})"
        rf" + ({e.w_agg_diff:.3f})({e.d_agg:.2f}) = \mathbf{{{e.z:.4f}}}"
    )
    st.latex(
        rf"P(\text{{Time 1 vence}}) = \frac{{1}}{{1 + e^{{-z}}}} = \frac{{1}}{{1 + e^{{-({e.z:.4f})}}}}"
        rf" = \mathbf{{{e.prob_pct:.2f}\%}}"
    )
    st.altair_chart(sigmoid_chart(e.z, e.prob_pct), width="stretch")
    st.caption("Curva sigmoide: a faixa verde (48% a 52%) é a **zona de equilíbrio**. O ponto azul é esta partida.")
    st.markdown("**🧾 Trecho SQL responsável:**")
    st.code(SQL_REGRESSAO, language="sql")

