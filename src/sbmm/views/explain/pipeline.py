"""Diagrama geral do pipeline executado no PostgreSQL."""

import streamlit as st

_DOT = """
digraph {
    rankdir=LR; bgcolor="transparent";
    node [
        shape=box,
        style="rounded,filled",
        fontname="Helvetica",
        fontsize=11,
        fillcolor="#151926",
        color="#7c3aed",
        fontcolor="#f1f5f9",
        penwidth=1.3
    ];
    edge [color="#8b5cf6", fontcolor="#cbd5e1", fontname="Helvetica", fontsize=10];
    app [label="Streamlit\\n(Python)", fillcolor="#1e1b4b", color="#8b5cf6", fontcolor="#ddd6fe"];
    subgraph cluster_pg {
        label="PostgreSQL + pgvector (Supabase) — 1 única chamada RPC";
        fontname="Helvetica"; fontsize=11; fontcolor="#c4b5fd";
        style="rounded,dashed"; color="#8b5cf6"; bgcolor="#0e111a";
        v [label="1. Vetor 4D\\ndo âncora"];
        k [label="2. KNN no\\níndice HNSW"];
        s [label="3. Snake Draft\\nABBA"];
        r [label="4. Regressão\\nLogística"];
        v -> k -> s -> r;
    }
    res [label="10 jogadores\\n+ probabilidade", fillcolor="#062e22", color="#10b981", fontcolor="#a7f3d0"];
    app -> v [label=" anchor_id"];
    r -> res;
    res -> app [style=dashed, color="#64748b", label=" JSON"];
}"""


def render(latencia_ms: float) -> None:
    st.graphviz_chart(_DOT, width="stretch")
    st.caption(
        f"O Python envia **apenas o ID do jogador**. Todas as etapas abaixo rodam dentro do PostgreSQL "
        f"e só o resultado final (10 linhas) volta para a aplicação, em **{latencia_ms:.1f} ms** no total."
    )

