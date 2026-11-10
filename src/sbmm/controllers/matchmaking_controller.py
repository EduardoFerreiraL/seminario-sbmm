"""Fluxo da página: carrega a fila, trata o clique, guarda o estado e delega às views."""

from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

from sbmm.config.settings import Settings
from sbmm.domain.errors import ConfigError, DataAccessError, MatchmakingError
from sbmm.infra.supabase_client import create_supabase
from sbmm.repositories import MatchmakingRepository, ModelRepository, PlayerRepository
from sbmm.services import MatchmakingService
from sbmm.views import anchor_panel, explain, match_result

log = logging.getLogger(__name__)
_STATE_KEY = "resultado"


@st.cache_resource(show_spinner=False)
def build_service() -> MatchmakingService:
    """Composição das dependências (uma vez por processo do Streamlit)."""
    settings = Settings.from_env()
    log.info("Configuração carregada: %r", settings)
    client = create_supabase(settings)
    return MatchmakingService(PlayerRepository(client), ModelRepository(client), MatchmakingRepository(client))


@st.cache_data(ttl=60, show_spinner=False)
def _load_queue(_service: MatchmakingService) -> pd.DataFrame:
    # Carrega a fila inteira para o seletor e o gráfico do espaço vetorial
    return _service.list_queue()


def _show_data_error(err: DataAccessError) -> None:
    st.error(
        f"⚠️ Não foi possível concluir a operação **{err.operation}** no Supabase. "
        "Verifique a conexão, as chaves no `.env` e se os scripts de `sql/migrations/` foram aplicados. "
        "Detalhes técnicos foram registrados no terminal."
    )


class MatchmakingController:
    def __init__(self, service: MatchmakingService) -> None:
        self._service = service

    def run(self) -> None:
        try:
            df_players = _load_queue(self._service)
        except DataAccessError as err:
            _show_data_error(err)
            return

        if df_players.empty:
            st.warning("Nenhum jogador encontrado na fila (`players_mmr`). Execute `run seed` primeiro.")
            return

        col1, col2 = st.columns([1, 2], gap="large")
        with col1:
            anchor_row, executar = anchor_panel.render(df_players)
        with col2:
            st.subheader("2. Resultado do Cluster KNN + Predição dentro do SGBD")
            anchor_id = int(anchor_row["player_id"])
            if executar:
                self._execute(anchor_id)
            self._render_result(df_players, anchor_row, anchor_id)

    def _execute(self, anchor_id: int) -> None:
        with st.spinner("Consultando índice HNSW e executando inferência SQL no PostgreSQL..."):
            try:
                match = self._service.execute(anchor_id)
                outcome: dict = {"anchor_id": anchor_id, "match": match, "expl": self._service.explain(match)}
            except MatchmakingError as err:
                outcome = {"anchor_id": anchor_id, "error": err}
            except DataAccessError as err:
                outcome = {"anchor_id": anchor_id, "error": err}
        # Guarda o resultado para ele não sumir quando a página for reexecutada
        st.session_state[_STATE_KEY] = outcome

    def _render_result(self, df_players: pd.DataFrame, anchor_row: pd.Series, anchor_id: int) -> None:
        resultado = st.session_state.get(_STATE_KEY)
        if not resultado or resultado["anchor_id"] != anchor_id:
            st.info(
                "👈 Selecione um jogador âncora ao lado e clique em **Executar Matchmaking In-DB** "
                "para formar a partida em tempo real."
            )
            return

        err = resultado.get("error")
        if isinstance(err, MatchmakingError):
            match_result.render_invalid_match(err)
            return
        if isinstance(err, DataAccessError):
            _show_data_error(err)
            return

        match = resultado["match"]
        match_result.render_metrics(match)
        tab_partida, tab_logica = st.tabs(["🎯 Partida Formada", "🧠 Como o SGBD chegou aqui"])
        with tab_partida:
            match_result.render_teams(match)
        with tab_logica:
            explain.render(df_players, anchor_row, match, resultado["expl"])


def get_controller() -> MatchmakingController | None:
    """Monta o controller; em caso de configuração inválida, mostra o erro e retorna None."""
    try:
        return MatchmakingController(build_service())
    except ConfigError as err:
        st.error(f"⚠️ Configuração inválida: {err}")
    except Exception:  # noqa: BLE001
        log.exception("Falha ao inicializar a aplicação")
        st.error("⚠️ Falha ao conectar ao Supabase. Detalhes técnicos foram registrados no terminal.")
    return None

