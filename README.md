# 🎮 Skill-Based Matchmaking (SBMM) com In-Database ML

Demonstração prática de **Skill-Based Matchmaking (SBMM)** aplicado ao League of Legends utilizando **In-Database Machine Learning** no **PostgreSQL + pgvector (Supabase)** e interface interativa em **Streamlit**.

## 🚀 Arquitetura

- **Busca Vetorial KNN (`pgvector` / HNSW)**: Vetorização normalizada de atributos dos jogadores na fila (`mmr`, `winrate`, `aggression_score`, `avg_game_duration`) para encontrar os vizinhos mais próximos diretamente no SGBD.
- **Inferência In-Database (Regressão Logística em SQL)**: Cálculo da probabilidade de vitória do Time 1 vs Time 2 dentro da função RPC `matchmake_in_db` no PostgreSQL, sem tráfego desnecessário de dados para a aplicação.
- **Dashboard Interativo (`Streamlit`)**: Visualização em tempo real dos times formados, distância vetorial máxima, probabilidade de equilíbrio (48%–52%) e latência da RPC.

## 📂 Estrutura do Projeto

- `popular_supabase.py`: Lê o dataset `games.csv` do League of Legends, popula o histórico de partidas (`lol_matches_history`) e gera 300 jogadores vetorizados na fila (`players_mmr`).
- `app_demo.py`: Aplicação Streamlit que consome a RPC `matchmake_in_db` do Supabase e exibe o pareamento ao vivo.
- `requirements.txt`: Dependências Python do projeto.
- `.env.example`: Exemplo de configuração das variáveis de ambiente do Supabase.

## ⚙️ Como Executar

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Copie o arquivo `.env.example` para `.env` e preencha suas credenciais do Supabase (`SUPABASE_URL` e `SUPABASE_KEY`).
3. Coloque o dataset `games.csv` na raiz do projeto e popule o banco:
   ```bash
   python popular_supabase.py
   ```
4. Inicie a demonstração com Streamlit:
   ```bash
   streamlit run app_demo.py
   ```

### ⚡ Atalho: `run dev`

Instale o projeto uma vez em modo editável para criar o comando `run`:

```bash
pip install -e .
run dev       # inicia o Streamlit (app_demo.py)
run seed      # popula o Supabase (popular_supabase.py)
run install   # instala o requirements.txt
```

> Se o `pip` avisar que a pasta `Scripts` não está no PATH, adicione-a ao PATH ou use os atalhos locais: `run dev` no **cmd**, `.\run dev` no **PowerShell**, ou `python dev.py dev`.

## 🧠 Explicabilidade (aba "Como o SGBD chegou aqui")

Após executar o matchmaking, a aba **🧠 Como o SGBD chegou aqui** mostra o pipeline em 4 etapas (Vetorização → KNN/HNSW → Snake Draft → Regressão Logística), cada uma com explicação, dados reais da partida e o trecho SQL responsável, além de uma **prova de consistência** automática.

Para que os intermediários venham do próprio PostgreSQL e o plano de execução (`EXPLAIN ANALYZE`) apareça, rode uma vez o arquivo `explain_helpers.sql` no SQL Editor do Supabase. Ele cria `matchmake_explain` e `explain_knn` e ajusta `matchmake_in_db` para que o índice HNSW possa ser usado. Sem ele, o app funciona normalmente e recalcula os intermediários no Python.
