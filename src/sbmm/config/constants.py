"""Constantes do domínio compartilhadas entre app, seed e testes.

Devem permanecer em sincronia com o SQL em ``sql/migrations/002_functions.sql``.
"""

# --- Times e Snake Draft (mesma regra do CASE WHEN no SQL) ---
TEAM_AZUL = "Time 1 (Azul)"
TEAM_VERM = "Time 2 (Vermelho)"
SNAKE_T1_RANKS: tuple[int, ...] = (1, 4, 5, 8, 9)
MATCH_SIZE = 10

# --- Modelo de regressão logística armazenado no SGBD ---
MODEL_NAME = "sbmm_logistic_v1"
BALANCE_MIN, BALANCE_MAX = 48.0, 52.0  # faixa de "equilíbrio ideal" (%)

# --- Normalização do vetor 4D (skill_vector) ---
MMR_MIN, MMR_MAX = 800.0, 2600.0
WR_MIN, WR_MAX = 35.0, 72.0
AGG_MAX = 12.0
DUR_MAX_MIN = 60.0

# --- Cores dos gráficos (otimizadas para tema escuro) ---
COR_AZUL, COR_VERM, COR_FILA, COR_ANCORA = "#3b82f6", "#f43f5e", "#475569", "#f59e0b"

# --- Colunas numéricas vindas do banco ---
PLAYER_NUMERIC_COLS = ("mmr", "winrate", "aggression_score", "avg_game_duration")
MATCH_NUMERIC_COLS = ("mmr", "winrate", "aggression_score", "vector_distance", "predicted_team1_win_prob")

