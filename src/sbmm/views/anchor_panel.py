"""Coluna 1: seleção do jogador âncora."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from sbmm.views import styles


def render(df_players: pd.DataFrame) -> tuple[pd.Series, bool]:
    """Desenha o seletor e as métricas do âncora. Retorna (linha do âncora, botão clicado)."""
    styles.render_section_title("01", "Jogador Âncora na Fila", f"{len(df_players)} na fila")
    # Seleciona pelo player_id (único) e exibe o nome: evita ambiguidade com nomes repetidos
    names = dict(zip(df_players["player_id"].astype(int), df_players["summoner_name"]))
    selected_id = st.selectbox(
        "Escolha um jogador procurando partida:",
        options=list(names),
        format_func=lambda pid: names[pid],
    )
    anchor_row = df_players[df_players["player_id"].astype(int) == selected_id].iloc[0]

    with st.container(border=True):
        styles.render_player_card_header(
            str(anchor_row["summoner_name"]),
            int(anchor_row["player_id"]),
            str(anchor_row["main_role"]),
        )
        c_m1, c_m2 = st.columns(2)
        c_m1.metric("MMR Atual", f"{anchor_row['mmr']:.1f} pts")
        c_m2.metric("Role Principal", anchor_row["main_role"])

        c_m3, c_m4 = st.columns(2)
        c_m3.metric("Winrate", f"{anchor_row['winrate']:.2f}%")
        c_m4.metric("Agressividade", f"{anchor_row['aggression_score']:.2f}")

        if "avg_game_duration" in anchor_row and pd.notna(anchor_row["avg_game_duration"]):
            styles.render_player_card_footer(float(anchor_row["avg_game_duration"]))

    executar = st.button(
        "⚡ Executar Matchmaking In-DB (SQL RPC)",
        type="primary",
        width="stretch",
    )
    return anchor_row, executar

