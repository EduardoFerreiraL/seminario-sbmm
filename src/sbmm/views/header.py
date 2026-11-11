"""Cabeçalho da página."""

import streamlit as st


def render() -> None:
    st.markdown(
        """
        <div class="sbmm-header">
            <div class="sbmm-badge-row">
                <span class="sbmm-pill">PostgreSQL + pgvector</span>
                <span class="sbmm-pill">HNSW Index (KNN 4D)</span>
                <span class="sbmm-pill">In-Database Logistic Regression</span>
                <span class="sbmm-pill sbmm-pill-neutral">League of Legends · 5v5</span>
            </div>
            <h1 class="sbmm-header-title">🎮 Skill-Based Matchmaking com In-Database ML</h1>
            <p class="sbmm-header-sub">
                Demonstração ao vivo: <strong>KNN Vetorial (HNSW)</strong> + <strong>Snake Draft ABBA</strong> +
                <strong>Regressão Logística em SQL</strong> executados 100% dentro do SGBD em uma única chamada RPC.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

