"""Trechos SQL exibidos na aba de explicação (copiados de sql/migrations/002_functions.sql)."""

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


def executed_calls(anchor_id: int) -> str:
    """Chamadas SQL executadas para o âncora (exibidas no expander final)."""
    aid = int(anchor_id)
    return (
        f"-- Resultado da partida (medido na latência)\n"
        f"SELECT * FROM matchmake_in_db({aid});\n\n"
        f"-- Intermediários da regressão (aba de explicação)\n"
        f"SELECT * FROM matchmake_explain({aid});\n\n"
        f"-- Plano de execução da busca KNN\n"
        f"SELECT * FROM explain_knn({aid});"
    )

