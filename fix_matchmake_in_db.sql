-- Correção da função matchmake_in_db
-- Bug: ROW_NUMBER() era calculado ANTES do LIMIT 10, ou seja, ranqueava a fila inteira
-- por MMR. Os 10 vizinhos KNN recebiam ranks como 3, 57, 212..., que quase nunca caem em
-- (1,4,5,8,9) -> Time 1 ficava vazio e a probabilidade virava NULL.
-- Correção: primeiro seleciona os 10 vizinhos (LIMIT), depois ranqueia só esses 10.

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
    WITH anchor AS (
        SELECT skill_vector FROM players_mmr p WHERE p.player_id = anchor_player_id
    ),
    knn_raw AS (
        -- Busca os 10 jogadores mais próximos no espaço vetorial 4D (usa o índice HNSW)
        SELECT
            p.player_id,
            p.summoner_name,
            p.main_role,
            p.mmr,
            p.winrate,
            p.aggression_score,
            ROUND((p.skill_vector <-> a.skill_vector)::numeric, 4)::FLOAT AS dist
        FROM players_mmr p, anchor a
        WHERE p.in_queue = TRUE
        ORDER BY p.skill_vector <-> a.skill_vector
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

