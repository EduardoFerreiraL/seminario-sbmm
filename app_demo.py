import os
import json
import math
import re
import time
import altair as alt
import pandas as pd
import httpx
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

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

TEAM_AZUL = "Time 1 (Azul)"
TEAM_VERM = "Time 2 (Vermelho)"
SNAKE_T1_RANKS = (1, 4, 5, 8, 9)  # Mesma regra do CASE WHEN dentro do SQL
COR_AZUL, COR_VERM, COR_FILA, COR_ANCORA = "#1f77b4", "#d62728", "#c7c7c7", "#f5b700"

# ==========================================
# TRECHOS SQL EXIBIDOS NA ABA DE EXPLICAÇÃO
# (copiados de explain_helpers.sql / matchmake_in_db)
# ==========================================
SQL_VETOR = """-- Coluna vetorial do pgvector (4 dimensões normalizadas entre 0 e 1)
skill_vector vector(4)   -- [mmr_norm, winrate_norm, agressividade_norm, duracao_norm]

-- Índice de vizinhos aproximados (Hierarchical Navigable Small World) - definição equivalente
CREATE INDEX ON players_mmr USING hnsw (skill_vector vector_l2_ops);"""

SQL_KNN = """knn_raw AS (
    SELECT p.*,
           p.skill_vector <-> (SELECT skill_vector FROM players_mmr
                               WHERE player_id = anchor_player_id) AS dist
    FROM players_mmr p
    WHERE p.in_queue = TRUE
    ORDER BY dist          -- <-> = distância Euclidiana (L2) -> usa o índice HNSW
    LIMIT 10               -- os 10 vizinhos mais próximos = 1 partida 5x5
)"""

SQL_SNAKE = """knn_cluster AS (
    SELECT k.*, ROW_NUMBER() OVER (ORDER BY k.mmr DESC, k.player_id) AS rk
    FROM knn_raw k                      -- ranqueia SÓ os 10 vizinhos por MMR
),
teams_split AS (
    SELECT c.*,
           CASE WHEN c.rk IN (1, 4, 5, 8, 9) THEN 'Time 1 (Azul)'
                ELSE 'Time 2 (Vermelho)' END AS team    -- Snake Draft ABBA
    FROM knn_cluster c
)"""

SQL_REGRESSAO = """-- Médias de cada time (CTE team_averages)
AVG(CASE WHEN team = 'Time 1 (Azul)' THEN mmr END) AS t1_mmr, ...

-- predict_team1_win_prob(...)
SELECT * INTO w FROM ml_model_weights WHERE model_name = 'sbmm_logistic_v1';
z := w.intercept
   + w.w_mmr_diff * (t1_mmr - t2_mmr)
   + w.w_wr_diff  * (t1_wr  - t2_wr)
   + w.w_agg_diff * (t1_agg - t2_agg);     -- produto escalar
prob := 1.0 / (1.0 + exp(-z));             -- sigmoide
RETURN ROUND((prob * 100)::numeric, 2);"""


@st.cache_resource
def get_supabase() -> Client:
    verify_ssl = os.getenv("SUPABASE_VERIFY_SSL", "true").lower() != "false"
    try:
        c = create_client(SUPABASE_URL, SUPABASE_KEY, options=ClientOptions(httpx_client=httpx.Client(verify=verify_ssl)))
        c.table("players_mmr").select("player_id").limit(1).execute()
        return c
    except Exception as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e) or "certificate verify failed" in str(e).lower():
            return create_client(SUPABASE_URL, SUPABASE_KEY, options=ClientOptions(httpx_client=httpx.Client(verify=False)))
        raise


def _parse_vector(v):
    """pgvector chega via PostgREST como texto '[0.1,0.2,...]'."""
    if isinstance(v, str):
        return json.loads(v)
    return list(v) if v is not None else None


@st.cache_data(ttl=60)
def load_queue_players() -> pd.DataFrame:
    # Carrega a fila inteira (300 jogadores) para o gráfico do espaço vetorial
    res = (
        get_supabase()
        .table("players_mmr")
        .select("player_id, summoner_name, main_role, mmr, winrate, aggression_score, avg_game_duration, skill_vector")
        .eq("in_queue", True)
        .order("mmr", desc=True)
        .execute()
    )
    df = pd.DataFrame(res.data)
    if not df.empty:
        df["skill_vector"] = df["skill_vector"].apply(_parse_vector)
        for c in ["mmr", "winrate", "aggression_score", "avg_game_duration"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


@st.cache_data(ttl=300)
def load_model_weights() -> dict | None:
    res = get_supabase().table("ml_model_weights").select("*").eq("model_name", "sbmm_logistic_v1").execute()
    return res.data[0] if res.data else None


def fetch_explanations(anchor_id: int) -> dict:
    """Busca no SGBD os intermediários (matchmake_explain) e o plano de execução (explain_knn).
    Se as funções ainda não foram criadas (explain_helpers.sql), devolve None e o app usa fallback."""
    out = {"explain": None, "explain_err": None, "plan": None, "plan_forced": None, "plan_err": None}
    try:
        r = supabase.rpc("matchmake_explain", {"anchor_player_id": anchor_id}).execute()
        out["explain"] = r.data[0] if r.data else None
    except Exception as e:  # noqa: BLE001
        out["explain_err"] = str(e)
    try:
        r = supabase.rpc("explain_knn", {"anchor_player_id": anchor_id, "force_index": False}).execute()
        out["plan"] = _plan_lines(r.data)
        if not knn_usou_indice(out["plan"]):
            r2 = supabase.rpc("explain_knn", {"anchor_player_id": anchor_id, "force_index": True}).execute()
            out["plan_forced"] = _plan_lines(r2.data)
    except Exception as e:  # noqa: BLE001
        out["plan_err"] = str(e)
    return out


def knn_usou_indice(plan: list[str]) -> bool:
    """True se a varredura da FILA (alias p) foi feita por índice.
    A linha do âncora (alias a) usa a chave primária e não conta."""
    return any(re.search(r"Index Scan using \S+ on players_mmr p\b", ln) for ln in plan or [])


def _plan_lines(data) -> list[str]:
    # RETURNS SETOF TEXT pode vir como lista de strings ou lista de dicts
    lines = []
    for item in data or []:
        lines.append(next(iter(item.values())) if isinstance(item, dict) else str(item))
    return lines


def snake_ranking(df_match: pd.DataFrame) -> pd.DataFrame:
    """Reconstrói no Python o ROW_NUMBER() + CASE do SQL, para conferência."""
    d = df_match.sort_values(["mmr", "player_id"], ascending=[False, True]).reset_index(drop=True)
    d["rk"] = d.index + 1
    d["time_recalculado"] = d["rk"].apply(lambda r: TEAM_AZUL if r in SNAKE_T1_RANKS else TEAM_VERM)
    return d


def compute_explain_python(df_match: pd.DataFrame, w: dict) -> dict:
    """Fallback (se matchmake_explain não existir): mesmos cálculos do SQL, feitos no Python."""
    t1 = df_match[df_match["assigned_team"] == TEAM_AZUL]
    t2 = df_match[df_match["assigned_team"] == TEAM_VERM]
    e = {
        "model_name": w["model_name"],
        "t1_mmr": t1["mmr"].mean(), "t2_mmr": t2["mmr"].mean(),
        "t1_wr": t1["winrate"].mean(), "t2_wr": t2["winrate"].mean(),
        "t1_agg": t1["aggression_score"].mean(), "t2_agg": t2["aggression_score"].mean(),
        "intercept": float(w["intercept"]), "w_mmr_diff": float(w["w_mmr_diff"]),
        "w_wr_diff": float(w["w_wr_diff"]), "w_agg_diff": float(w["w_agg_diff"]),
    }
    for k in ("mmr", "wr", "agg"):
        e[f"d_{k}"] = e[f"t1_{k}"] - e[f"t2_{k}"]
        e[f"contrib_{k}"] = e[f"w_{k}_diff"] * e[f"d_{k}"]
    e["z"] = e["intercept"] + e["contrib_mmr"] + e["contrib_wr"] + e["contrib_agg"]
    e["prob_pct"] = round(100 / (1 + math.exp(-e["z"])), 2)
    return e


# ==========================================
# RENDERIZAÇÃO DA ABA "COMO O SGBD CHEGOU AQUI"
# ==========================================
def render_pipeline_overview(latencia_ms: float):
    dot = """
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
    st.graphviz_chart(dot, width="stretch")
    st.caption(
        f"O Python envia **apenas o ID do jogador**. Todas as etapas abaixo rodam dentro do PostgreSQL "
        f"e só o resultado final (10 linhas) volta para a aplicação, em **{latencia_ms:.1f} ms** no total."
    )


def render_etapa_vetor(anchor_row: pd.Series):
    st.markdown(
        "**💡 O que acontece:** cada jogador é representado como um **ponto num espaço de 4 dimensões**. "
        "Os valores são normalizados entre 0 e 1 para que nenhuma métrica domine a distância "
        "(sem isso, o MMR, que vai até 2600, pesaria muito mais que o winrate)."
    )
    vec = anchor_row["skill_vector"] or [None] * 4
    df_vec = pd.DataFrame(
        {
            "Dimensão": ["MMR", "Winrate (%)", "Agressividade", "Duração média (min)"],
            "Valor bruto": [anchor_row["mmr"], anchor_row["winrate"], anchor_row["aggression_score"], anchor_row["avg_game_duration"]],
            "Normalização": ["(mmr − 800) / 1800", "(wr − 35) / 37", "agg / 12", "min(dur / 60, 1)"],
            "Valor no vetor (SGBD)": vec,
        }
    )
    st.markdown(f"**📊 Vetor do jogador âncora `{anchor_row['summoner_name']}`:**")
    st.dataframe(
        df_vec,
        hide_index=True,
        column_config={
            "Valor bruto": st.column_config.NumberColumn(format="%.2f"),
            "Valor no vetor (SGBD)": st.column_config.ProgressColumn(format="%.4f", min_value=0.0, max_value=1.0),
        },
    )
    st.code(f"skill_vector = {json.dumps(vec)}", language="sql")
    st.markdown("**🧾 Estrutura no banco:**")
    st.code(SQL_VETOR, language="sql")


def render_etapa_knn(df_players: pd.DataFrame, df_match: pd.DataFrame, anchor_row: pd.Series, expl: dict):
    st.markdown(
        "**💡 O que acontece:** o operador `<->` do pgvector calcula a **distância Euclidiana** entre o vetor do "
        "âncora e o de cada jogador da fila. O `ORDER BY ... LIMIT 10` devolve os 10 mais próximos, e o "
        "**índice HNSW** (um grafo de navegação) encontra esses vizinhos **sem comparar com a fila inteira**."
    )
    st.latex(r"d(a,b) = \sqrt{\sum_{i=1}^{4} (a_i - b_i)^2}")

    # --- Gráfico do espaço vetorial (projeção 2D) ---
    anchor_id = int(anchor_row["player_id"])
    team_by_id = dict(zip(df_match["player_id"].astype(int), df_match["assigned_team"]))
    plot = df_players[["player_id", "summoner_name", "mmr", "winrate", "aggression_score"]].copy()
    plot["Grupo"] = plot["player_id"].astype(int).map(team_by_id).fillna("Fila (não selecionado)")
    plot.loc[plot["player_id"].astype(int) == anchor_id, "Grupo"] = "⭐ Âncora"

    escala = alt.Scale(
        domain=["Fila (não selecionado)", TEAM_AZUL, TEAM_VERM, "⭐ Âncora"],
        range=[COR_FILA, COR_AZUL, COR_VERM, COR_ANCORA],
    )
    base = alt.Chart(plot).encode(
        x=alt.X("mmr:Q", title="MMR", scale=alt.Scale(zero=False)),
        y=alt.Y("winrate:Q", title="Winrate (%)", scale=alt.Scale(zero=False)),
        color=alt.Color("Grupo:N", scale=escala, legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["summoner_name", "mmr", "winrate", "aggression_score", "Grupo"],
    )
    fila = base.transform_filter(alt.datum.Grupo == "Fila (não selecionado)").mark_circle(size=35, opacity=0.5)
    vizinhos = base.transform_filter(
        (alt.datum.Grupo == TEAM_AZUL) | (alt.datum.Grupo == TEAM_VERM)
    ).mark_circle(size=120, opacity=0.95, stroke="white", strokeWidth=1)
    ancora = base.transform_filter(alt.datum.Grupo == "⭐ Âncora").mark_point(
        shape="diamond", size=350, filled=True, stroke="black", strokeWidth=1
    )
    st.markdown("**📊 Onde estão os 10 vizinhos dentro da fila (300 jogadores):**")
    st.altair_chart((fila + vizinhos + ancora).properties(height=340).interactive(), width="stretch")
    st.caption(
        "Projeção 2D (MMR × Winrate) de um espaço que, na verdade, tem 4 dimensões. Um ponto que parece "
        "distante aqui pode estar próximo em **agressividade** e **duração média**, e vice-versa."
    )

    viz = df_match.sort_values("vector_distance")[["summoner_name", "assigned_team", "mmr", "winrate", "vector_distance"]]
    st.dataframe(
        viz,
        hide_index=True,
        column_config={
            "summoner_name": "Invocador",
            "assigned_team": "Time atribuído",
            "mmr": st.column_config.NumberColumn("MMR", format="%.1f"),
            "winrate": st.column_config.NumberColumn("Winrate (%)", format="%.2f"),
            "vector_distance": st.column_config.ProgressColumn(
                "Distância ao âncora", format="%.4f", min_value=0.0, max_value=float(max(viz["vector_distance"].max(), 1e-9))
            ),
        },
    )

    st.markdown("**🧾 Trecho SQL responsável:**")
    st.code(SQL_KNN, language="sql")

    # --- Prova técnica: plano de execução real ---
    st.markdown("**🔬 Prova técnica: plano de execução real do PostgreSQL (`EXPLAIN ANALYZE`)**")
    if expl["plan_err"]:
        st.warning(
            "A função `explain_knn` ainda não existe no banco. Rode o arquivo `explain_helpers.sql` "
            "no SQL Editor do Supabase para habilitar esta prova."
        )
        return
    plan = expl["plan"] or []
    usou_indice = knn_usou_indice(plan)
    if usou_indice:
        st.success("✅ O otimizador escolheu **Index Scan** no índice HNSW para encontrar os vizinhos.")
        st.code("\n".join(plan), language="text")
    else:
        st.info(
            "Com apenas 300 jogadores, o otimizador do PostgreSQL considerou a **varredura sequencial** "
            "(Seq Scan) mais barata que o índice. Isso é esperado em tabelas pequenas: o HNSW compensa em "
            "filas grandes (milhares a milhões de jogadores)."
        )
        c1, c2 = st.columns(2)
        with c1:
            st.caption("Plano escolhido livremente pelo otimizador:")
            st.code("\n".join(plan), language="text")
        with c2:
            st.caption("Mesmo SQL com `enable_seqscan = off` (força o índice):")
            st.code("\n".join(expl["plan_forced"] or ["(sem retorno)"]), language="text")


def render_etapa_snake(df_snake: pd.DataFrame):
    st.markdown(
        "**💡 O que acontece:** os 10 vizinhos são ordenados por MMR (do maior para o menor) e distribuídos em "
        "**zigue-zague** (Snake Draft ABBA). Assim, o melhor jogador fica no Time 1, mas o Time 2 recebe o 2º e o 3º, "
        "e assim por diante, o que equilibra a soma de MMR."
    )
    padrao = " ".join("🔵" if r in SNAKE_T1_RANKS else "🔴" for r in range(1, 11))
    st.markdown(f"**Padrão de escolha (posição 1 → 10):** {padrao}")

    show = df_snake[["rk", "assigned_team", "summoner_name", "mmr"]].copy()
    show["Escolha"] = show["rk"].apply(lambda r: "A" if r in SNAKE_T1_RANKS else "B")
    st.dataframe(
        show[["rk", "Escolha", "assigned_team", "summoner_name", "mmr"]],
        hide_index=True,
        column_config={
            "rk": st.column_config.NumberColumn("Posição (rk)"),
            "assigned_team": "Time",
            "summoner_name": "Invocador",
            "mmr": st.column_config.NumberColumn("MMR", format="%.1f"),
        },
    )
    s1 = df_snake.loc[df_snake["assigned_team"] == TEAM_AZUL, "mmr"].sum()
    s2 = df_snake.loc[df_snake["assigned_team"] == TEAM_VERM, "mmr"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Σ MMR 🔵 Time 1", f"{s1:.1f}")
    c2.metric("Σ MMR 🔴 Time 2", f"{s2:.1f}")
    c3.metric("Diferença", f"{abs(s1 - s2):.1f}")
    st.markdown("**🧾 Trecho SQL responsável:**")
    st.code(SQL_SNAKE, language="sql")


def sigmoid_chart(z: float, prob_pct: float) -> alt.LayerChart:
    lim = max(4.0, abs(z) + 1.0)
    pts = [-lim + i * (2 * lim) / 200 for i in range(201)]
    curve = pd.DataFrame({"z": pts, "P": [100 / (1 + math.exp(-x)) for x in pts]})
    zona = alt.Chart(pd.DataFrame({"y1": [48], "y2": [52]})).mark_rect(opacity=0.25, color="#2ca02c").encode(
        y="y1:Q", y2="y2:Q"
    )
    linha = alt.Chart(curve).mark_line(color="#555555").encode(
        x=alt.X("z:Q", title="z (combinação linear)"),
        y=alt.Y("P:Q", title="P(vitória Time 1) %", scale=alt.Scale(domain=[0, 100])),
    )
    ponto = alt.Chart(pd.DataFrame({"z": [z], "P": [prob_pct]})).mark_point(
        size=250, filled=True, color=COR_AZUL, stroke="black"
    ).encode(x="z:Q", y="P:Q", tooltip=["z", "P"])
    return (zona + linha + ponto).properties(height=260)


def render_etapa_regressao(e: dict, origem_sgbd: bool):
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
            "no Python com os pesos do banco. Rode `explain_helpers.sql` no Supabase para que eles venham do SGBD."
        )

    tabela = pd.DataFrame(
        {
            "Feature": ["MMR médio", "Winrate médio (%)", "Agressividade média"],
            "🔵 Time 1": [e["t1_mmr"], e["t1_wr"], e["t1_agg"]],
            "🔴 Time 2": [e["t2_mmr"], e["t2_wr"], e["t2_agg"]],
            "Δ (T1 − T2)": [e["d_mmr"], e["d_wr"], e["d_agg"]],
            "Peso (w)": [e["w_mmr_diff"], e["w_wr_diff"], e["w_agg_diff"]],
            "Contribuição (w·Δ)": [e["contrib_mmr"], e["contrib_wr"], e["contrib_agg"]],
        }
    )
    st.markdown(f"**📊 Entradas do modelo `{e['model_name']}`:**")
    st.dataframe(
        tabela,
        hide_index=True,
        column_config={c: st.column_config.NumberColumn(format="%.4f") for c in tabela.columns[1:]},
    )

    st.markdown("**Fórmula com os valores desta partida:**")
    st.latex(r"z = \beta_0 + w_{mmr}\,\Delta_{mmr} + w_{wr}\,\Delta_{wr} + w_{agg}\,\Delta_{agg}")
    st.latex(
        rf"z = {e['intercept']:.3f} + ({e['w_mmr_diff']:.3f})({e['d_mmr']:.2f}) + ({e['w_wr_diff']:.3f})({e['d_wr']:.2f})"
        rf" + ({e['w_agg_diff']:.3f})({e['d_agg']:.2f}) = \mathbf{{{e['z']:.4f}}}"
    )
    st.latex(
        rf"P(\text{{Time 1 vence}}) = \frac{{1}}{{1 + e^{{-z}}}} = \frac{{1}}{{1 + e^{{-({e['z']:.4f})}}}}"
        rf" = \mathbf{{{float(e['prob_pct']):.2f}\%}}"
    )
    st.altair_chart(sigmoid_chart(float(e["z"]), float(e["prob_pct"])), width="stretch")
    st.caption("Curva sigmoide: a faixa verde (48% a 52%) é a **zona de equilíbrio**. O ponto azul é esta partida.")
    st.markdown("**🧾 Trecho SQL responsável:**")
    st.code(SQL_REGRESSAO, language="sql")


def render_prova_consistencia(df_snake: pd.DataFrame, e: dict, win_prob: float, origem_sgbd: bool):
    st.markdown("#### ✅ Prova de consistência")
    st.caption("Conferências automáticas que mostram que a explicação acima corresponde ao que o SGBD executou.")

    times_ok = bool((df_snake["time_recalculado"] == df_snake["assigned_team"]).all())
    p_formula = 100 / (1 + math.exp(-float(e["z"])))
    formula_ok = abs(round(p_formula, 2) - win_prob) < 0.011
    explain_ok = abs(float(e["prob_pct"]) - win_prob) < 0.011

    checks = [
        ("Snake Draft recalculado no Python gera os **mesmos times** que o SQL", times_ok),
        (f"Sigmoide aplicada ao z ({float(e['z']):.4f}) = **{p_formula:.2f}%**, igual à RPC (**{win_prob:.2f}%**)", formula_ok),
        (
            f"Probabilidade dos intermediários ({'SGBD' if origem_sgbd else 'Python'}) = **{float(e['prob_pct']):.2f}%**, "
            f"igual à `matchmake_in_db` (**{win_prob:.2f}%**)",
            explain_ok,
        ),
    ]
    for txt, ok in checks:
        st.markdown(f"{'✅' if ok else '❌'} {txt}")


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
    anchor_id = int(anchor_row["player_id"])

    if executar:
        with st.spinner("Consultando índice HNSW e executando inferência SQL no PostgreSQL..."):
            t0 = time.perf_counter()
            rpc_res = supabase.rpc(
                "matchmake_in_db",
                {"anchor_player_id": anchor_id},
            ).execute()
            latencia_ms = (time.perf_counter() - t0) * 1000
            # Chamadas extras (fora da medição de latência) só para a aba de explicação
            explicacoes = fetch_explanations(anchor_id)
        # Guarda o resultado para ele não sumir quando a página for reexecutada
        st.session_state["resultado"] = {
            "anchor_id": anchor_id,
            "data": rpc_res.data,
            "latencia_ms": latencia_ms,
            "expl": explicacoes,
        }

    resultado = st.session_state.get("resultado")
    if resultado and resultado["anchor_id"] == anchor_id:
        latencia_ms = resultado["latencia_ms"]
        expl = resultado["expl"]
        df_match = pd.DataFrame(resultado["data"])
        for c in ["mmr", "winrate", "aggression_score", "vector_distance"]:
            if c in df_match:
                df_match[c] = pd.to_numeric(df_match[c], errors="coerce")

        # A RPC pode devolver predicted_team1_win_prob = NULL quando um dos times
        # fica vazio (média de 0 linhas = NULL no SQL). Validamos antes de converter.
        n_t1 = int((df_match.get("assigned_team") == TEAM_AZUL).sum()) if not df_match.empty else 0
        n_t2 = int((df_match.get("assigned_team") == TEAM_VERM).sum()) if not df_match.empty else 0
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

        tab_partida, tab_logica = st.tabs(["🎯 Partida Formada", "🧠 Como o SGBD chegou aqui"])

        with tab_partida:
            cols_exibicao = ["summoner_name", "main_role", "mmr", "winrate", "vector_distance"]
            col_config = {
                "summoner_name": st.column_config.TextColumn("Invocador"),
                "main_role": st.column_config.TextColumn("Role"),
                "mmr": st.column_config.NumberColumn("MMR", format="%.1f"),
                "winrate": st.column_config.NumberColumn("Winrate (%)", format="%.2f%%"),
                "vector_distance": st.column_config.NumberColumn("Distância KNN", format="%.4f"),
            }

            t_azul = df_match[df_match["assigned_team"] == TEAM_AZUL][cols_exibicao]
            t_verm = df_match[df_match["assigned_team"] == TEAM_VERM][cols_exibicao]

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

        with tab_logica:
            df_snake = snake_ranking(df_match)
            origem_sgbd = expl["explain"] is not None
            if origem_sgbd:
                e = {k: (float(v) if k != "model_name" and v is not None else v) for k, v in expl["explain"].items()}
            else:
                pesos = load_model_weights()
                e = compute_explain_python(df_match, pesos) if pesos else None

            render_pipeline_overview(latencia_ms)

            with st.expander("**Etapa 1 · Vetorização do jogador (pgvector)**"):
                render_etapa_vetor(anchor_row)
            with st.expander("**Etapa 2 · Busca dos 10 vizinhos mais próximos (KNN + índice HNSW)**"):
                render_etapa_knn(df_players, df_match, anchor_row, expl)
            with st.expander("**Etapa 3 · Divisão dos times (Snake Draft ABBA)**"):
                render_etapa_snake(df_snake)
            with st.expander("**Etapa 4 · Probabilidade de vitória (Regressão Logística em SQL)**"):
                if e:
                    render_etapa_regressao(e, origem_sgbd)
                else:
                    st.error("Não foi possível obter os pesos do modelo (`ml_model_weights`).")

            if e:
                render_prova_consistencia(df_snake, e, win_prob, origem_sgbd)

            with st.expander("🔍 Ver chamadas SQL executadas pelo SGBD"):
                st.code(
                    f"-- Resultado da partida (medido na latência)\n"
                    f"SELECT * FROM matchmake_in_db({anchor_id});\n\n"
                    f"-- Intermediários da regressão (aba de explicação)\n"
                    f"SELECT * FROM matchmake_explain({anchor_id});\n\n"
                    f"-- Plano de execução da busca KNN\n"
                    f"SELECT * FROM explain_knn({anchor_id});",
                    language="sql",
                )
    else:
        st.info("👈 Selecione um jogador âncora ao lado e clique em **Executar Matchmaking In-DB** para formar a partida em tempo real.")
