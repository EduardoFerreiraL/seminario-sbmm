"""Gráficos Altair. Funções retornam o chart (testáveis sem Streamlit)."""

from __future__ import annotations

import altair as alt
import pandas as pd

from sbmm.config.constants import BALANCE_MAX, BALANCE_MIN, COR_ANCORA, COR_AZUL, COR_FILA, COR_VERM, TEAM_AZUL, TEAM_VERM
from sbmm.domain.matchmaking import sigmoid_pct

GRUPO_FILA = "Fila (não selecionado)"
GRUPO_ANCORA = "⭐ Âncora"


def vector_space_chart(df_players: pd.DataFrame, df_match: pd.DataFrame, anchor_id: int) -> alt.LayerChart:
    """Projeção 2D (MMR × Winrate) da fila, destacando os 10 vizinhos e o âncora."""
    team_by_id = dict(zip(df_match["player_id"].astype(int), df_match["assigned_team"]))
    plot = df_players[["player_id", "summoner_name", "mmr", "winrate", "aggression_score"]].copy()
    plot["Grupo"] = plot["player_id"].astype(int).map(team_by_id).fillna(GRUPO_FILA)
    plot.loc[plot["player_id"].astype(int) == int(anchor_id), "Grupo"] = GRUPO_ANCORA

    escala = alt.Scale(
        domain=[GRUPO_FILA, TEAM_AZUL, TEAM_VERM, GRUPO_ANCORA],
        range=[COR_FILA, COR_AZUL, COR_VERM, COR_ANCORA],
    )
    base = alt.Chart(plot).encode(
        x=alt.X("mmr:Q", title="MMR", scale=alt.Scale(zero=False)),
        y=alt.Y("winrate:Q", title="Winrate (%)", scale=alt.Scale(zero=False)),
        color=alt.Color("Grupo:N", scale=escala, legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["summoner_name", "mmr", "winrate", "aggression_score", "Grupo"],
    )
    fila = base.transform_filter(alt.datum.Grupo == GRUPO_FILA).mark_circle(size=35, opacity=0.5)
    vizinhos = base.transform_filter(
        (alt.datum.Grupo == TEAM_AZUL) | (alt.datum.Grupo == TEAM_VERM)
    ).mark_circle(size=120, opacity=0.95, stroke="white", strokeWidth=1)
    ancora = base.transform_filter(alt.datum.Grupo == GRUPO_ANCORA).mark_point(
        shape="diamond", size=350, filled=True, stroke="black", strokeWidth=1
    )
    return (fila + vizinhos + ancora).properties(height=340).interactive()


def sigmoid_chart(z: float, prob_pct: float) -> alt.LayerChart:
    """Curva sigmoide com a zona de equilíbrio e o ponto da partida."""
    lim = max(4.0, abs(z) + 1.0)
    pts = [-lim + i * (2 * lim) / 200 for i in range(201)]
    curve = pd.DataFrame({"z": pts, "P": [sigmoid_pct(x) for x in pts]})
    zona = alt.Chart(pd.DataFrame({"y1": [BALANCE_MIN], "y2": [BALANCE_MAX]})).mark_rect(
        opacity=0.25, color="#2ca02c"
    ).encode(y="y1:Q", y2="y2:Q")
    linha = alt.Chart(curve).mark_line(color="#555555").encode(
        x=alt.X("z:Q", title="z (combinação linear)"),
        y=alt.Y("P:Q", title="P(vitória Time 1) %", scale=alt.Scale(domain=[0, 100])),
    )
    ponto = alt.Chart(pd.DataFrame({"z": [z], "P": [prob_pct]})).mark_point(
        size=250, filled=True, color=COR_AZUL, stroke="black"
    ).encode(x="z:Q", y="P:Q", tooltip=["z", "P"])
    return (zona + linha + ponto).properties(height=260)

