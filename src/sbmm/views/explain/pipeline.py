"""Diagrama geral do pipeline executado no PostgreSQL."""

import streamlit as st

_DOT = """
digraph {
    rankdir=LR; bgcolor="transparent";
    node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, fillcolor="#f0f2f6", color="#888888"];
    edge [color="#666666"];
    app [label="Streamlit\\n(Python)", fillcolor="#fff3cd"];
    subgraph cluster_pg {
        label="PostgreSQL + pgvector (Supabase) — 1 única chamada RPC";
        fontname="Helvetica"; fontsize=11; style="rounded,dashed"; color="#1f77b4";
        v [label="1. Vetor 4D\\ndo âncora"];
        k [label="2. KNN no\\níndice HNSW"];
        s [label="3. Snake Draft\\nABBA"];
        r [label="4. Regressão\\nLogística"];
        v -> k -> s -> r;
    }
    res [label="10 jogadores\\n+ probabilidade", fillcolor="#d4edda"];
    app -> v [label=" anchor_id"];
    r -> res;
    res -> app [style=dashed, label=" JSON"];
}"""


def render(latencia_ms: float) -> None:
    st.graphviz_chart(_DOT, width="stretch")
    st.caption(
        f"O Python envia **apenas o ID do jogador**. Todas as etapas abaixo rodam dentro do PostgreSQL "
        f"e só o resultado final (10 linhas) volta para a aplicação, em **{latencia_ms:.1f} ms** no total."
    )

