"""Métricas principais e aba "Partida Formada"."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from sbmm.config.constants import BALANCE_MAX, BALANCE_MIN, TEAM_AZUL, TEAM_VERM
from sbmm.domain.errors import MatchmakingError
from sbmm.domain.models import MatchResult
from sbmm.views import styles

_COLS = ["summoner_name", "main_role", "mmr", "winrate", "vector_distance"]


def render_metrics(match: MatchResult) -> None:
    equilibrado = BALANCE_MIN <= match.win_prob <= BALANCE_MAX
    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Probabilidade Vitória Time 1 (In-DB ML)",
        f"{match.win_prob:.2f}%",
        delta=f"Equilíbrio Ideal ({BALANCE_MIN:.0f}% - {BALANCE_MAX:.0f}%)"
        if equilibrado
        else f"Fora da faixa {BALANCE_MIN:.0f}%-{BALANCE_MAX:.0f}%",
        delta_color="normal" if equilibrado else "off",
    )
    m2.metric("Distância Vetorial Máxima (KNN)", f"{match.max_distance:.4f}")
    m3.metric("Tempo de Resposta Total (RPC)", f"{match.latency_ms:.1f} ms")
    styles.render_balance_bar(match.win_prob, BALANCE_MIN, BALANCE_MAX)


def _team_table(title: str, team: pd.DataFrame, *, is_team_blue: bool) -> None:
    col_config = {
        "summoner_name": st.column_config.TextColumn("Invocador"),
        "main_role": st.column_config.TextColumn("Role"),
        "mmr": st.column_config.NumberColumn("MMR", format="%.1f"),
        "winrate": st.column_config.NumberColumn("Winrate (%)", format="%.2f%%"),
        "vector_distance": st.column_config.NumberColumn("Distância KNN", format="%.4f"),
    }
    with st.container(border=True):
        styles.render_team_header(
            title,
            float(team["mmr"].mean()),
            float(team["winrate"].mean()),
            is_team_blue=is_team_blue,
        )
        st.dataframe(team, column_config=col_config, width="stretch", hide_index=True)


def render_teams(match: MatchResult) -> None:
    df = match.players
    c_azul, c_verm = st.columns(2)
    with c_azul:
        _team_table("🔵 Time 1 (Azul)", df[df["assigned_team"] == TEAM_AZUL][_COLS], is_team_blue=True)
    with c_verm:
        _team_table("🔴 Time 2 (Vermelho)", df[df["assigned_team"] == TEAM_VERM][_COLS], is_team_blue=False)


def render_invalid_match(err: MatchmakingError) -> None:
    st.error(f"⚠️ {err}")
    if isinstance(err.raw, pd.DataFrame) and not err.raw.empty:
        st.caption("Retorno bruto da RPC, para diagnóstico:")
        st.dataframe(err.raw, width="stretch", hide_index=True)

