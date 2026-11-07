-- =====================================================================
-- EXPLICABILIDADE DO MATCHMAKING (rodar no SQL Editor do Supabase)
-- =====================================================================
-- Este arquivo cria/atualiza 3 funções:
--   1. matchmake_in_db     -> mesma lógica de antes, mas agora o KNN usa de fato o índice HNSW
--   2. matchmake_explain   -> devolve os números INTERMEDIÁRIOS calculados pelo próprio SGBD
--                            (médias dos times, deltas, pesos, contribuições, z e probabilidade)
--   3. explain_knn         -> devolve o plano de execução (EXPLAIN ANALYZE) da busca KNN,
--                            provando qual estratégia o PostgreSQL usou (Index Scan HNSW x Seq Scan)
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. matchmake_in_db (correção para uso do índice HNSW)
-- ---------------------------------------------------------------------
-- Antes: "FROM players_mmr p, anchor a ... ORDER BY p.skill_vector <-> a.skill_vector"
--   -> o vetor de referência vinha de um JOIN, e o pgvector só usa o índice HNSW quando
--      o lado direito do operador <-> é um VALOR CONSTANTE para a consulta.
-- Agora: o vetor do âncora vem de uma subconsulta escalar (vira um parâmetro "InitPlan"),
--   o que permite o "Index Scan using ...hnsw...". O resultado é idêntico.
CREATE OR REPLACE FUNCTION matchmake_in_db(anchor_player_id INT)
RETURNS TABLE (
    assigned_team TEXT,
    player_id INT,
    summoner_name TEXT,
    main_role TEXT,
    mmr NUMERIC,
    winrate NUMERIC,
    aggression_score NUMERIC,
    vector_distance FLOAT,
    predicted_team1_win_prob NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH knn_raw AS (
        -- Busca os 10 jogadores mais próximos no espaço vetorial 4D (usa o índice HNSW)
        SELECT
            p.player_id,
            p.summoner_name,
            p.main_role,
            p.mmr,
            p.winrate,
            p.aggression_score,
            ROUND((p.skill_vector <-> (SELECT a.skill_vector FROM players_mmr a WHERE a.player_id = anchor_player_id))::numeric, 4)::FLOAT AS dist
        FROM players_mmr p
        WHERE p.in_queue = TRUE
        ORDER BY p.skill_vector <-> (SELECT a.skill_vector FROM players_mmr a WHERE a.player_id = anchor_player_id)
        LIMIT 10
    ),
    knn_cluster AS (
        -- Ranking por MMR apenas entre os 10 vizinhos já escolhidos
        SELECT
            k.*,
            ROW_NUMBER() OVER (ORDER BY k.mmr DESC, k.player_id) AS rk
        FROM knn_raw k
    ),
    teams_split AS (
        -- Snake Draft (ABBA): 1,4,5,8,9 -> Time 1 | 2,3,6,7,10 -> Time 2
        SELECT
            c.*,
            CASE WHEN c.rk IN (1, 4, 5, 8, 9) THEN 'Time 1 (Azul)' ELSE 'Time 2 (Vermelho)' END AS team
        FROM knn_cluster c
    ),
    team_averages AS (
        SELECT
            AVG(CASE WHEN t.team = 'Time 1 (Azul)' THEN t.mmr END) AS t1_mmr,
            AVG(CASE WHEN t.team = 'Time 2 (Vermelho)' THEN t.mmr END) AS t2_mmr,
            AVG(CASE WHEN t.team = 'Time 1 (Azul)' THEN t.winrate END) AS t1_wr,
            AVG(CASE WHEN t.team = 'Time 2 (Vermelho)' THEN t.winrate END) AS t2_wr,
            AVG(CASE WHEN t.team = 'Time 1 (Azul)' THEN t.aggression_score END) AS t1_agg,
            AVG(CASE WHEN t.team = 'Time 2 (Vermelho)' THEN t.aggression_score END) AS t2_agg
        FROM teams_split t
    )
    SELECT
        ts.team,
        ts.player_id,
        ts.summoner_name,
        ts.main_role,
        ts.mmr,
        ts.winrate,
        ts.aggression_score,
        ts.dist,
        predict_team1_win_prob(ta.t1_mmr::FLOAT, ta.t2_mmr::FLOAT, ta.t1_wr::FLOAT, ta.t2_wr::FLOAT, ta.t1_agg::FLOAT, ta.t2_agg::FLOAT)
    FROM teams_split ts
    CROSS JOIN team_averages ta
    ORDER BY ts.team, ts.mmr DESC;
END;
$$ LANGUAGE plpgsql;


-- ---------------------------------------------------------------------
-- 2. matchmake_explain: intermediários da Regressão Logística, calculados no SGBD
-- ---------------------------------------------------------------------
-- Reutiliza o resultado de matchmake_in_db (mesmos times) e expõe cada termo da fórmula:
--   z = intercept + w_mmr*ΔMMR + w_wr*ΔWR + w_agg*ΔAGG ;  P = 1 / (1 + e^-z)
CREATE OR REPLACE FUNCTION matchmake_explain(anchor_player_id INT)
RETURNS TABLE (
    model_name TEXT,
    t1_mmr FLOAT, t2_mmr FLOAT, d_mmr FLOAT,
    t1_wr  FLOAT, t2_wr  FLOAT, d_wr  FLOAT,
    t1_agg FLOAT, t2_agg FLOAT, d_agg FLOAT,
    intercept FLOAT, w_mmr_diff FLOAT, w_wr_diff FLOAT, w_agg_diff FLOAT,
    contrib_mmr FLOAT, contrib_wr FLOAT, contrib_agg FLOAT,
    z FLOAT,
    prob_pct NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH m AS (
        SELECT * FROM matchmake_in_db(anchor_player_id)
    ),
    avgs AS (
        SELECT
            AVG(CASE WHEN m.assigned_team = 'Time 1 (Azul)'     THEN m.mmr END)::FLOAT              AS a1_mmr,
            AVG(CASE WHEN m.assigned_team = 'Time 2 (Vermelho)' THEN m.mmr END)::FLOAT              AS a2_mmr,
            AVG(CASE WHEN m.assigned_team = 'Time 1 (Azul)'     THEN m.winrate END)::FLOAT          AS a1_wr,
            AVG(CASE WHEN m.assigned_team = 'Time 2 (Vermelho)' THEN m.winrate END)::FLOAT          AS a2_wr,
            AVG(CASE WHEN m.assigned_team = 'Time 1 (Azul)'     THEN m.aggression_score END)::FLOAT AS a1_agg,
            AVG(CASE WHEN m.assigned_team = 'Time 2 (Vermelho)' THEN m.aggression_score END)::FLOAT AS a2_agg
        FROM m
    ),
    terms AS (
        SELECT
            w.model_name::TEXT AS mn,
            a.*,
            w.intercept::FLOAT  AS b0,
            w.w_mmr_diff::FLOAT AS b_mmr,
            w.w_wr_diff::FLOAT  AS b_wr,
            w.w_agg_diff::FLOAT AS b_agg
        FROM avgs a
        CROSS JOIN ml_model_weights w
        WHERE w.model_name = 'sbmm_logistic_v1'
    )
    SELECT
        t.mn,
        t.a1_mmr, t.a2_mmr, t.a1_mmr - t.a2_mmr,
        t.a1_wr,  t.a2_wr,  t.a1_wr  - t.a2_wr,
        t.a1_agg, t.a2_agg, t.a1_agg - t.a2_agg,
        t.b0, t.b_mmr, t.b_wr, t.b_agg,
        t.b_mmr * (t.a1_mmr - t.a2_mmr),
        t.b_wr  * (t.a1_wr  - t.a2_wr),
        t.b_agg * (t.a1_agg - t.a2_agg),
        t.b0 + t.b_mmr * (t.a1_mmr - t.a2_mmr) + t.b_wr * (t.a1_wr - t.a2_wr) + t.b_agg * (t.a1_agg - t.a2_agg),
        predict_team1_win_prob(t.a1_mmr, t.a2_mmr, t.a1_wr, t.a2_wr, t.a1_agg, t.a2_agg)
    FROM terms t;
END;
$$ LANGUAGE plpgsql;


-- ---------------------------------------------------------------------
-- 3. explain_knn: plano de execução real da busca KNN
-- ---------------------------------------------------------------------
-- force_index = FALSE -> plano escolhido livremente pelo otimizador
-- force_index = TRUE  -> desliga o Seq Scan só nesta transação (SET LOCAL), útil porque
--                        com poucas linhas (300) o otimizador pode achar a varredura mais barata.
CREATE OR REPLACE FUNCTION explain_knn(anchor_player_id INT, force_index BOOLEAN DEFAULT FALSE)
RETURNS SETOF TEXT AS $$
DECLARE
    line TEXT;
BEGIN
    IF force_index THEN
        PERFORM set_config('enable_seqscan', 'off', true);
    END IF;

    FOR line IN EXECUTE format(
        'EXPLAIN (ANALYZE, COSTS OFF, TIMING ON, SUMMARY ON)
         SELECT p.player_id
         FROM players_mmr p
         WHERE p.in_queue = TRUE
         ORDER BY p.skill_vector <-> (SELECT a.skill_vector FROM players_mmr a WHERE a.player_id = %s)
         LIMIT 10',
        anchor_player_id
    )
    LOOP
        RETURN NEXT line;
    END LOOP;

    IF force_index THEN
        PERFORM set_config('enable_seqscan', 'on', true);
    END IF;
END;
$$ LANGUAGE plpgsql;

