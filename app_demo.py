import os
import time
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

# ==========================================
# CONFIGURAÇÃO E CONEXÃO (.env)
# ==========================================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

st.set_page_config(
    page_title="SBMM In-Database ML - LoL",
    page_icon="🎮",
    layout="wide",
)

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Variáveis `SUPABASE_URL` e `SUPABASE_KEY` não encontradas no arquivo `.env`.")
    st.stop()


@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


@st.cache_data(ttl=60)
def load_queue_players() -> pd.DataFrame:
    res = (
        get_supabase()
        .table("players_mmr")
        .select("player_id, summoner_name, main_role, mmr, winrate, aggression_score")
        .eq("in_queue", True)
        .order("mmr", desc=True)
        .limit(100)
        .execute()
    )
    return pd.DataFrame(res.data)


supabase = get_supabase()

# ==========================================
# CABEÇALHO
# ==========================================
st.title("🎮 Skill-Based Matchmaking com In-Database ML (PostgreSQL + pgvector)")
st.markdown(
    "Demonstração ao vivo: **KNN Vetorial (HNSW)** + **Regressão Logística em SQL** rodando 100% dentro do SGBD."
)
st.divider()

df_players = load_queue_players()

if df_players.empty:
    st.warning("Nenhum jogador encontrado na fila (`players_mmr`). Execute `py popular_supabase.py` primeiro.")
    st.stop()

col1, col2 = st.columns([1, 2], gap="large")

# ==========================================
# COLUNA 1: SELEÇÃO DO JOGADOR ÂNCORA
# ==========================================
with col1:
    st.subheader("1. Jogador Âncora na Fila")
    selected_name = st.selectbox(
        "Escolha um jogador procurando partida:",
        df_players["summoner_name"],
    )
    anchor_row = df_players[df_players["summoner_name"] == selected_name].iloc[0]

    with st.container(border=True):
        c_m1, c_m2 = st.columns(2)
        c_m1.metric("MMR Atual", f"{anchor_row['mmr']:.1f} pts")
        c_m2.metric("Role Principal", anchor_row["main_role"])

        c_m3, c_m4 = st.columns(2)
        c_m3.metric("Winrate", f"{anchor_row['winrate']:.2f}%")
        c_m4.metric("Agressividade", f"{anchor_row['aggression_score']:.2f}")

    executar = st.button(
        "⚡ Executar Matchmaking In-DB (SQL RPC)",
        type="primary",
        width="stretch",
    )

# ==========================================
# COLUNA 2: RESULTADO DO MATCHMAKING IN-DB
# ==========================================
with col2:
    st.subheader("2. Resultado do Cluster KNN + Predição dentro do SGBD")
    if executar:
        with st.spinner("Consultando índice HNSW e executando inferência SQL no PostgreSQL..."):
            t0 = time.perf_counter()
            rpc_res = supabase.rpc(
                "matchmake_in_db",
                {"anchor_player_id": int(anchor_row["player_id"])},
            ).execute()
            latencia_ms = (time.perf_counter() - t0) * 1000

        df_match = pd.DataFrame(rpc_res.data)

        # A RPC pode devolver predicted_team1_win_prob = NULL quando um dos times
        # fica vazio (média de 0 linhas = NULL no SQL). Validamos antes de converter.
        n_t1 = int((df_match.get("assigned_team") == "Time 1 (Azul)").sum()) if not df_match.empty else 0
        n_t2 = int((df_match.get("assigned_team") == "Time 2 (Vermelho)").sum()) if not df_match.empty else 0
        prob_serie = (
            pd.to_numeric(df_match["predicted_team1_win_prob"], errors="coerce").dropna()
            if "predicted_team1_win_prob" in df_match
            else pd.Series(dtype=float)
        )

        if df_match.empty or prob_serie.empty or n_t1 == 0 or n_t2 == 0:
            st.error(
                "⚠️ A função `matchmake_in_db` não conseguiu formar dois times para este jogador "
                f"(Time 1: {n_t1} jogadores | Time 2: {n_t2} jogadores), "
                "então a probabilidade de vitória veio `NULL`."
            )
            st.caption("Retorno bruto da RPC, para diagnóstico:")
            st.dataframe(df_match, width="stretch", hide_index=True)
            st.stop()

        win_prob = float(prob_serie.iloc[0])
        equilibrado = 48.0 <= win_prob <= 52.0

        m1, m2, m3 = st.columns(3)
        m1.metric(
            "Probabilidade Vitória Time 1 (In-DB ML)",
            f"{win_prob:.2f}%",
            delta="Equilíbrio Ideal (48% - 52%)" if equilibrado else "Fora da faixa 48%-52%",
            delta_color="normal" if equilibrado else "off",
        )
        m2.metric(
            "Distância Vetorial Máxima (KNN)",
            f"{df_match['vector_distance'].max():.4f}",
        )
        m3.metric("Tempo de Resposta Total (RPC)", f"{latencia_ms:.1f} ms")

        cols_exibicao = ["summoner_name", "main_role", "mmr", "winrate", "vector_distance"]
        col_config = {
            "summoner_name": st.column_config.TextColumn("Invocador"),
            "main_role": st.column_config.TextColumn("Role"),
            "mmr": st.column_config.NumberColumn("MMR", format="%.1f"),
            "winrate": st.column_config.NumberColumn("Winrate (%)", format="%.2f%%"),
            "vector_distance": st.column_config.NumberColumn("Distância KNN", format="%.4f"),
        }

        t_azul = df_match[df_match["assigned_team"] == "Time 1 (Azul)"][cols_exibicao]
        t_verm = df_match[df_match["assigned_team"] == "Time 2 (Vermelho)"][cols_exibicao]

        c_azul, c_verm = st.columns(2)
        with c_azul:
            st.markdown("#### 🔵 Time 1 (Azul)")
            st.dataframe(t_azul, column_config=col_config, width="stretch", hide_index=True)
            st.caption(
                f"**MMR Médio:** {t_azul['mmr'].mean():.1f} | **Winrate Médio:** {t_azul['winrate'].mean():.1f}%"
            )
        with c_verm:
            st.markdown("#### 🔴 Time 2 (Vermelho)")
            st.dataframe(t_verm, column_config=col_config, width="stretch", hide_index=True)
            st.caption(
                f"**MMR Médio:** {t_verm['mmr'].mean():.1f} | **Winrate Médio:** {t_verm['winrate'].mean():.1f}%"
            )

        with st.expander("🔍 Ver Query SQL Executada Internamente pelo SGBD"):
            st.code(
                f"SELECT * FROM matchmake_in_db({int(anchor_row['player_id'])});",
                language="sql",
            )
    else:
        st.info("👈 Selecione um jogador âncora ao lado e clique em **Executar Matchmaking In-DB** para formar a partida em tempo real.")
