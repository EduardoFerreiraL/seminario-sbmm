import os
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from supabase import create_client, Client

# ==========================================
# CONFIGURAÇÃO DO SUPABASE (.env)
# ==========================================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Defina SUPABASE_URL e SUPABASE_KEY no arquivo .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("1. Lendo dataset games.csv do League of Legends...")
df = pd.read_csv("games.csv")

# Seleciona uma amostra de 1.000 partidas reais para popular o histórico rápido
df_sample = df.sample(n=1000, random_state=42)

matches_payload = []
for _, row in df_sample.iterrows():
    matches_payload.append({
        "game_id": int(row["gameId"]),
        "game_duration": int(row["gameDuration"]),
        "winner": int(row["winner"]),
        "first_blood": int(row["firstBlood"]),
        "first_tower": int(row["firstTower"]),
        "first_baron": int(row["firstBaron"]),
        "t1_tower_kills": int(row["t1_towerKills"]),
        "t1_inhibitor_kills": int(row["t1_inhibitorKills"]),
        "t1_baron_kills": int(row["t1_baronKills"]),
        "t1_dragon_kills": int(row["t1_dragonKills"]),
        "t2_tower_kills": int(row["t2_towerKills"]),
        "t2_inhibitor_kills": int(row["t2_inhibitorKills"]),
        "t2_baron_kills": int(row["t2_baronKills"]),
        "t2_dragon_kills": int(row["t2_dragonKills"]),
    })

print("2. Enviando histórico de partidas do LoL para o Supabase...")
# Insere em lotes de 250 para evitar timeout
for i in range(0, len(matches_payload), 250):
    supabase.table("lol_matches_history").upsert(matches_payload[i:i+250]).execute()

print("3. Gerando 300 Jogadores na Fila derivados das métricas reais do dataset...")
np.random.seed(42)
roles = ["TOP", "JUNGLE", "MID", "ADC", "SUP"]
prefixes = ["Shadow", "Void", "Hex", "Cyber", "Arcane", "Rift", "Baron", "Draven", "Yasuo", "Vayne", "Kaisa", "Zed"]
suffixes = ["Slayer", "King", "Carry", "Main", "Diff", "Pro", "God", "Smurf", "BR", "X"]

# Usa a distribuição real de tempo de partida e objetivos do dataset do LoL
durations_min = (df["gameDuration"] / 60.0).values
aggression_base = ((df["t1_towerKills"] + df["t1_dragonKills"] * 2 + (df["firstBlood"] == 1).astype(int) * 3) / 2.5).clip(1, 10).values

players_payload = []
for idx in range(1, 301):
    mmr = float(np.round(np.clip(np.random.normal(1500, 320), 800, 2600), 1))
    # Correlaciona levemente o winrate com o MMR para dar realismo ao cluster
    wr = float(np.round(np.clip(50 + (mmr - 1500) * 0.015 + np.random.normal(0, 4.5), 35, 72), 2))
    agg = float(np.round(np.random.choice(aggression_base) + np.random.normal(0, 0.5), 2))
    dur = float(np.round(np.random.choice(durations_min), 1))
    
    # Vetor Normalizado [0 a 1] para o cálculo de Distância Euclidiana (KNN) no pgvector não ser dominado pelo MMR
    vec_mmr = round((mmr - 800) / (2600 - 800), 4)
    vec_wr  = round((wr - 35) / (72 - 35), 4)
    vec_agg = round(agg / 12.0, 4)
    vec_dur = round(min(dur / 60.0, 1.0), 4)
    
    players_payload.append({
        "summoner_name": f"{np.random.choice(prefixes)}{np.random.choice(suffixes)}#{1000 + idx}",
        "main_role": roles[idx % 5],
        "mmr": mmr,
        "winrate": wr,
        "aggression_score": agg,
        "avg_game_duration": dur,
        "in_queue": True,
        "skill_vector": [vec_mmr, vec_wr, vec_agg, vec_dur]
    })

supabase.table("players_mmr").upsert(players_payload).execute()
print("Concluído! Banco populado e vetorizado com sucesso no Supabase.")
