"""Estilização global (CSS) e componentes visuais de apoio (somente apresentação)."""

from __future__ import annotations

import html
import streamlit as st

# Paleta de cores sólida (Dark Carbon + detalhes em Roxo)
BG_PRIMARY = "#0b0d13"
BG_SURFACE = "#121520"
BG_ELEVATED = "#181c2b"
BORDER_SUBTLE = "#23283b"
PURPLE_MAIN = "#8b5cf6"
PURPLE_DARK = "#7c3aed"
PURPLE_LIGHT = "#c4b5fd"
TEXT_PRIMARY = "#f1f5f9"
TEXT_MUTED = "#94a3b8"

_ROLE_COLORS: dict[str, tuple[str, str, str]] = {
    "TOP": ("#f59e0b", "rgba(245, 158, 11, 0.12)", "rgba(245, 158, 11, 0.35)"),
    "JUNGLE": ("#10b981", "rgba(16, 185, 129, 0.12)", "rgba(16, 185, 129, 0.35)"),
    "MID": ("#c4b5fd", "rgba(139, 92, 246, 0.14)", "rgba(139, 92, 246, 0.40)"),
    "ADC": ("#60a5fa", "rgba(59, 130, 246, 0.12)", "rgba(59, 130, 246, 0.35)"),
    "SUP": ("#2dd4bf", "rgba(45, 212, 191, 0.12)", "rgba(45, 212, 191, 0.35)"),
}

_CSS = """
<style>
/* ====== Layout geral e fundo sólido ====== */
.stApp {
    background-color: #0b0d13;
    color: #f1f5f9;
}

header[data-testid="stHeader"] {
    background-color: rgba(11, 13, 19, 0.88);
    backdrop-filter: blur(6px);
}

.block-container {
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
    max-width: 1440px;
}

/* ====== Cards e containers com borda (sólidos, sem gradientes) ====== */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #121520 !important;
    border: 1px solid #23283b !important;
    border-radius: 10px !important;
    padding: 1rem 1.1rem !important;
    transition: border-color 0.18s ease;
}

div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: #38306b !important;
}

/* ====== Métricas (KPIs) ====== */
div[data-testid="stMetric"] {
    background-color: #151926;
    border: 1px solid #23283b;
    border-left: 3px solid #7c3aed;
    border-radius: 8px;
    padding: 0.75rem 0.95rem;
}

div[data-testid="stMetricLabel"] p {
    color: #94a3b8 !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

div[data-testid="stMetricValue"] {
    color: #f8fafc !important;
    font-weight: 700 !important;
}

/* ====== Botão Primário (Roxo sólido, sem gradiente) ====== */
button[kind="primary"],
button[data-testid="stBaseButton-primary"] {
    background-color: #7c3aed !important;
    color: #ffffff !important;
    border: 1px solid #8b5cf6 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.1rem !important;
    transition: background-color 0.15s ease, border-color 0.15s ease, transform 0.1s ease !important;
}

button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {
    background-color: #6d28d9 !important;
    border-color: #a78bfa !important;
}

button[kind="primary"]:active,
button[data-testid="stBaseButton-primary"]:active {
    background-color: #5b21b6 !important;
    transform: translateY(1px);
}

/* ====== Selectbox / Inputs ====== */
div[data-baseweb="select"] > div {
    background-color: #121520 !important;
    border-color: #262c40 !important;
    border-radius: 8px !important;
}

div[data-baseweb="select"] > div:hover,
div[data-baseweb="select"] > div:focus-within {
    border-color: #8b5cf6 !important;
}

/* ====== Abas (Tabs) ====== */
div[data-baseweb="tab-list"] {
    gap: 0.5rem;
    border-bottom: 1px solid #23283b !important;
    padding-bottom: 0px;
}

button[data-baseweb="tab"] {
    background-color: transparent !important;
    color: #94a3b8 !important;
    font-weight: 600 !important;
    padding: 0.55rem 1rem !important;
    border-radius: 6px 6px 0 0 !important;
}

button[data-baseweb="tab"]:hover {
    color: #e2e8f0 !important;
    background-color: #151926 !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #c4b5fd !important;
    background-color: rgba(139, 92, 246, 0.10) !important;
}

div[data-baseweb="tab-highlight"] {
    background-color: #8b5cf6 !important;
    height: 2px !important;
}

/* ====== Expanders (Aba de Explicação) ====== */
details[data-testid="stExpander"] {
    background-color: #121520 !important;
    border: 1px solid #23283b !important;
    border-radius: 8px !important;
    margin-bottom: 0.65rem !important;
}

details[data-testid="stExpander"][open] {
    border-color: #4c1d95 !important;
}

details[data-testid="stExpander"] > summary {
    padding: 0.7rem 1rem !important;
    color: #e2e8f0 !important;
}

details[data-testid="stExpander"] > summary:hover {
    color: #c4b5fd !important;
}

/* ====== Tabelas / Dataframes e Blocos de Código ====== */
div[data-testid="stDataFrame"] {
    border: 1px solid #23283b;
    border-radius: 8px;
    overflow: hidden;
}

div[data-testid="stCodeBlock"] pre {
    background-color: #0e111a !important;
    border: 1px solid #23283b !important;
    border-radius: 8px !important;
}

/* ====== Classes utilitárias dos componentes customizados ====== */
.sbmm-header {
    background-color: #121520;
    border: 1px solid #23283b;
    border-left: 4px solid #8b5cf6;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.5rem;
}

.sbmm-badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin-bottom: 0.65rem;
}

.sbmm-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    padding: 0.2rem 0.6rem;
    border-radius: 5px;
    background-color: rgba(139, 92, 246, 0.14);
    color: #c4b5fd;
    border: 1px solid rgba(139, 92, 246, 0.38);
}

.sbmm-pill-neutral {
    background-color: #181c2b;
    color: #94a3b8;
    border: 1px solid #262c40;
}

.sbmm-header-title {
    margin: 0 0 0.35rem 0;
    font-size: 1.55rem;
    font-weight: 700;
    color: #f8fafc;
    letter-spacing: -0.01em;
    line-height: 1.25;
}

.sbmm-header-sub {
    margin: 0;
    font-size: 0.92rem;
    color: #94a3b8;
}

.sbmm-header-sub strong {
    color: #ddd6fe;
    font-weight: 600;
}

.sbmm-section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.85rem;
    padding-bottom: 0.55rem;
    border-bottom: 1px solid #1e2336;
}

.sbmm-section-left {
    display: flex;
    align-items: center;
    gap: 0.6rem;
}

.sbmm-step-tag {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    padding: 0.2rem 0.5rem;
    border-radius: 5px;
    background-color: rgba(139, 92, 246, 0.16);
    color: #c4b5fd;
    border: 1px solid rgba(139, 92, 246, 0.42);
}

.sbmm-section-title {
    margin: 0;
    font-size: 1.08rem;
    font-weight: 600;
    color: #f1f5f9;
}

.sbmm-player-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding-bottom: 0.65rem;
    margin-bottom: 0.65rem;
    border-bottom: 1px solid #1f2437;
}

.sbmm-player-name {
    font-size: 0.98rem;
    font-weight: 700;
    color: #f8fafc;
}

.sbmm-player-id {
    font-size: 0.76rem;
    color: #64748b;
    font-family: monospace;
    margin-left: 0.35rem;
}

.sbmm-player-foot {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.78rem;
    color: #94a3b8;
    margin-top: 0.55rem;
    padding-top: 0.5rem;
    border-top: 1px solid #1f2437;
}

.sbmm-balance-box {
    background-color: #121520;
    border: 1px solid #23283b;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0 1rem 0;
}

.sbmm-balance-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.8rem;
    margin-bottom: 0.45rem;
}

.sbmm-balance-track {
    position: relative;
    height: 10px;
    background-color: #f43f5e;
    border-radius: 5px;
    overflow: hidden;
}

.sbmm-balance-fill-t1 {
    height: 100%;
    background-color: #3b82f6;
}

.sbmm-balance-zone {
    position: absolute;
    top: 0;
    bottom: 0;
    border-left: 2px dashed rgba(255, 255, 255, 0.85);
    border-right: 2px dashed rgba(255, 255, 255, 0.85);
    background-color: rgba(16, 185, 129, 0.22);
}

.sbmm-team-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.5rem;
    background-color: #151926;
    border: 1px solid #23283b;
    border-radius: 8px;
    padding: 0.6rem 0.85rem;
    margin-bottom: 0.6rem;
}

.sbmm-team-title {
    font-size: 0.96rem;
    font-weight: 700;
    color: #f8fafc;
    margin: 0;
}

.sbmm-team-stats {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
}

.sbmm-stat-chip {
    font-size: 0.74rem;
    font-weight: 600;
    color: #cbd5e1;
    background-color: #0e111a;
    border: 1px solid #252b3d;
    border-radius: 5px;
    padding: 0.15rem 0.5rem;
}

.sbmm-empty-card {
    background-color: #121520;
    border: 1px dashed #2e354f;
    border-radius: 10px;
    padding: 2.2rem 1.5rem;
    text-align: center;
    margin-top: 0.4rem;
}

.sbmm-empty-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 42px;
    height: 42px;
    border-radius: 8px;
    background-color: rgba(139, 92, 246, 0.14);
    border: 1px solid rgba(139, 92, 246, 0.38);
    color: #c4b5fd;
    font-size: 1.2rem;
    margin-bottom: 0.75rem;
}

.sbmm-empty-title {
    font-size: 1rem;
    font-weight: 600;
    color: #f1f5f9;
    margin: 0 0 0.35rem 0;
}

.sbmm-empty-desc {
    font-size: 0.86rem;
    color: #94a3b8;
    max-width: 520px;
    margin: 0 auto;
    line-height: 1.45;
}

.sbmm-check-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    background-color: #151926;
    border: 1px solid #23283b;
    border-radius: 7px;
    padding: 0.55rem 0.85rem;
    margin-bottom: 0.45rem;
    font-size: 0.86rem;
    color: #e2e8f0;
}
</style>
"""


def inject_global_styles() -> None:
    """Injeta a folha de estilos global (tema escuro sólido com acentos em roxo)."""
    st.markdown(_CSS, unsafe_allow_html=True)


def render_section_title(step: str, title: str, right_badge: str | None = None) -> None:
    """Renderiza o cabeçalho de uma coluna com badge roxo de etapa."""
    esc_step = html.escape(step)
    esc_title = html.escape(title)
    right_html = (
        f'<span class="sbmm-pill sbmm-pill-neutral">{html.escape(right_badge)}</span>'
        if right_badge
        else ""
    )
    st.markdown(
        f"""
        <div class="sbmm-section-head">
            <div class="sbmm-section-left">
                <span class="sbmm-step-tag">ETAPA {esc_step}</span>
                <h3 class="sbmm-section-title">{esc_title}</h3>
            </div>
            {right_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_player_card_header(summoner_name: str, player_id: int, role: str) -> None:
    """Renderiza o topo do card do jogador âncora com nome, ID e badge da Role."""
    role_key = str(role).upper().strip()
    fg, bg, border = _ROLE_COLORS.get(role_key, ("#c4b5fd", "rgba(139, 92, 246, 0.14)", "rgba(139, 92, 246, 0.40)"))
    esc_name = html.escape(str(summoner_name))
    esc_role = html.escape(role_key)
    st.markdown(
        f"""
        <div class="sbmm-player-bar">
            <div>
                <span class="sbmm-player-name">{esc_name}</span>
                <span class="sbmm-player-id">ID #{int(player_id)}</span>
            </div>
            <span style="font-size:0.72rem;font-weight:700;padding:0.18rem 0.55rem;border-radius:5px;color:{fg};background-color:{bg};border:1px solid {border};">
                {esc_role}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_player_card_footer(avg_duration_min: float) -> None:
    """Exibe a 4ª dimensão do vetor (duração média de partida) no rodapé do card do âncora."""
    st.markdown(
        f"""
        <div class="sbmm-player-foot">
            <span>⏱️ Duração média de partida (4ª dimensão do vetor)</span>
            <strong style="color:#c4b5fd;">{avg_duration_min:.1f} min</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_balance_bar(win_prob: float, balance_min: float, balance_max: float) -> None:
    """Barra sólida de proporção Time 1 vs Time 2 destacando a faixa de equilíbrio (48%-52%)."""
    p1 = max(0.0, min(100.0, float(win_prob)))
    p2 = 100.0 - p1
    equilibrado = balance_min <= p1 <= balance_max
    status_txt = (
        f"Equilíbrio Ideal ({balance_min:.0f}%–{balance_max:.0f}%)"
        if equilibrado
        else f"Fora da faixa ideal ({balance_min:.0f}%–{balance_max:.0f}%)"
    )
    status_fg = "#34d399" if equilibrado else "#fbbf24"
    status_bg = "rgba(16, 185, 129, 0.14)" if equilibrado else "rgba(245, 158, 11, 0.14)"
    status_bd = "rgba(16, 185, 129, 0.40)" if equilibrado else "rgba(245, 158, 11, 0.40)"
    zone_width = max(0.0, balance_max - balance_min)

    st.markdown(
        f"""
        <div class="sbmm-balance-box">
            <div class="sbmm-balance-top">
                <span style="color:#60a5fa;font-weight:700;">🔵 Time 1: {p1:.2f}%</span>
                <span style="font-size:0.72rem;font-weight:700;padding:0.14rem 0.55rem;border-radius:4px;color:{status_fg};background:{status_bg};border:1px solid {status_bd};">
                    {status_txt}
                </span>
                <span style="color:#fb7185;font-weight:700;">🔴 Time 2: {p2:.2f}%</span>
            </div>
            <div class="sbmm-balance-track">
                <div class="sbmm-balance-fill-t1" style="width:{p1:.2f}%;"></div>
                <div class="sbmm-balance-zone" style="left:{balance_min:.2f}%;width:{zone_width:.2f}%;" title="Zona de Equilíbrio Ideal ({balance_min:.0f}% a {balance_max:.0f}%)"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_team_header(title: str, avg_mmr: float, avg_wr: float, *, is_team_blue: bool) -> None:
    """Cabeçalho sólido para a tabela de cada time com borda lateral Azul ou Vermelha."""
    accent = "#3b82f6" if is_team_blue else "#f43f5e"
    esc_title = html.escape(title)
    st.markdown(
        f"""
        <div class="sbmm-team-banner" style="border-left: 4px solid {accent};">
            <h4 class="sbmm-team-title">{esc_title}</h4>
            <div class="sbmm-team-stats">
                <span class="sbmm-stat-chip">MMR Médio: <strong style="color:#f8fafc;">{avg_mmr:.1f}</strong></span>
                <span class="sbmm-stat-chip">WR Médio: <strong style="color:#f8fafc;">{avg_wr:.1f}%</strong></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    """Card exibido antes de o usuário clicar no botão de executar matchmaking."""
    st.markdown(
        """
        <div class="sbmm-empty-card">
            <div class="sbmm-empty-icon">⚡</div>
            <p class="sbmm-empty-title">Pronto para formar a partida no SGBD</p>
            <p class="sbmm-empty-desc">
                Selecione um jogador âncora na coluna à esquerda e clique em
                <strong style="color:#c4b5fd;">Executar Matchmaking In-DB (SQL RPC)</strong>
                para consultar o índice HNSW (<code style="color:#c4b5fd;">pgvector</code>), dividir as equipes via
                Snake Draft e calcular a probabilidade de vitória em tempo real.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

