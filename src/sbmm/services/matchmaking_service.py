"""Casos de uso do matchmaking: executar a partida e montar a explicação."""

from __future__ import annotations

import logging
import time

import pandas as pd

from sbmm.config.constants import MATCH_NUMERIC_COLS
from sbmm.domain.errors import DataAccessError
from sbmm.domain.matchmaking import compute_regression_explain, snake_ranking, to_numeric, validate_match
from sbmm.domain.models import ExecutionPlan, Explanation, MatchResult, RegressionExplain
from sbmm.repositories import MatchmakingRepository, ModelRepository, PlayerRepository

log = logging.getLogger(__name__)


class MatchmakingService:
    def __init__(
        self,
        players: PlayerRepository,
        models: ModelRepository,
        matchmaking: MatchmakingRepository,
    ) -> None:
        self._players = players
        self._models = models
        self._matchmaking = matchmaking

    # ------------------------------------------------------------------ fila
    def list_queue(self) -> pd.DataFrame:
        return self._players.list_queue()

    # ------------------------------------------------------------- partida
    def execute(self, anchor_id: int) -> MatchResult:
        """Chama ``matchmake_in_db`` medindo apenas a latência dessa RPC.

        Raises:
            DataAccessError: falha de rede/permissão/função inexistente.
            MatchmakingError: a RPC respondeu, mas não formou dois times válidos.
        """
        t0 = time.perf_counter()
        rows = self._matchmaking.run_matchmaking(anchor_id)
        latency_ms = (time.perf_counter() - t0) * 1000

        df = to_numeric(pd.DataFrame(rows), MATCH_NUMERIC_COLS)
        win_prob = validate_match(df)
        log.info("Partida formada para âncora %s: P(T1)=%.2f%% em %.1f ms", anchor_id, win_prob, latency_ms)
        return MatchResult(anchor_id=anchor_id, players=df, win_prob=win_prob, latency_ms=latency_ms)

    # ----------------------------------------------------------- explicação
    def explain(self, match: MatchResult) -> Explanation:
        """Chamadas extras (fora da medição de latência) para a aba de explicabilidade.

        Nunca levanta exceção: se as funções de ``002_functions.sql`` não existirem no banco,
        usa o cálculo em Python (regressão) ou marca o plano como indisponível.
        """
        regression, from_db = self._regression(match)
        return Explanation(
            snake=snake_ranking(match.players),
            regression=regression,
            regression_from_db=from_db,
            plan=self._plan(match.anchor_id),
        )

    def _regression(self, match: MatchResult) -> tuple[RegressionExplain | None, bool]:
        try:
            row = self._matchmaking.explain_regression(match.anchor_id)
            if row is not None:
                return RegressionExplain.from_mapping(row), True
        except (DataAccessError, ValueError, KeyError) as exc:
            log.warning("matchmake_explain indisponível, usando fallback em Python: %s", exc)

        try:
            weights = self._models.get_weights()
        except DataAccessError:
            return None, False
        if weights is None:
            return None, False
        return compute_regression_explain(match.players, weights), False

    def _plan(self, anchor_id: int) -> ExecutionPlan:
        try:
            lines = self._matchmaking.explain_knn(anchor_id, force_index=False)
            forced = None
            if not ExecutionPlan(lines=lines).used_index:
                forced = self._matchmaking.explain_knn(anchor_id, force_index=True)
            return ExecutionPlan(lines=lines, forced_lines=forced)
        except DataAccessError as exc:
            log.warning("explain_knn indisponível: %s", exc)
            return ExecutionPlan(error=str(exc))

