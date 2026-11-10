"""Cabeçalho da página."""

import streamlit as st


def render() -> None:
    st.title("🎮 Skill-Based Matchmaking com In-Database ML (PostgreSQL + pgvector)")
    st.markdown(
        "Demonstração ao vivo: **KNN Vetorial (HNSW)** + **Regressão Logística em SQL** rodando 100% dentro do SGBD."
    )
    st.divider()

