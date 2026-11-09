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

### Pré-requisitos
- Python 3.10+ instalado.
- Arquivo `.env` configurado com `SUPABASE_URL` e `SUPABASE_KEY` (copie de `.env.example`).

### 1. Criar e ativar o ambiente virtual (Recomendado ao mudar de computador)

No **PowerShell**:
```powershell
# Cria o ambiente virtual
python -m venv .venv

# Ativa o ambiente
.\.venv\Scripts\Activate.ps1

# Instala as dependências
pip install -r requirements.txt
```

No **Prompt de Comando (CMD)**:
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
pip install -r requirements.txt
```

### 2. Iniciar a aplicação

Com o ambiente ativado:
```bash
streamlit run app_demo.py
```

Ou diretamente pelo caminho do ambiente virtual (sem precisar ativar):
```powershell
.\.venv\Scripts\streamlit.exe run app_demo.py
```

### ⚡ Atalhos de execução

Você pode usar os scripts utilitários inclusos na raiz:
- No **PowerShell**: `.\run.ps1 dev` ou `python dev.py dev`
- No **CMD**: `run.cmd dev` ou `run dev`
- Outros comandos: `dev` (dashboard), `seed` (popular banco), `install` (instalar dependências).

> **Dica de rede/firewall corporativo**: Caso esteja em uma rede com inspeção SSL/proxy (ex: Fortinet), a aplicação já possui fallback automático para contornar falhas de validação de certificado local.

## 🧠 Explicabilidade (aba "Como o SGBD chegou aqui")

Após executar o matchmaking, a aba **🧠 Como o SGBD chegou aqui** mostra o pipeline em 4 etapas (Vetorização → KNN/HNSW → Snake Draft → Regressão Logística), cada uma com explicação, dados reais da partida e o trecho SQL responsável, além de uma **prova de consistência** automática.

Para que os intermediários venham do próprio PostgreSQL e o plano de execução (`EXPLAIN ANALYZE`) apareça, rode uma vez o arquivo `explain_helpers.sql` no SQL Editor do Supabase. Ele cria `matchmake_explain` e `explain_knn` e ajusta `matchmake_in_db` para que o índice HNSW possa ser usado. Sem ele, o app funciona normalmente e recalcula os intermediários no Python.
