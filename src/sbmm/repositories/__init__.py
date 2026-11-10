"""Repositórios: único lugar do código que conversa com o Supabase."""

from sbmm.repositories.matchmaking_repository import MatchmakingRepository
from sbmm.repositories.model_repository import ModelRepository
from sbmm.repositories.player_repository import PlayerRepository

__all__ = ["MatchmakingRepository", "ModelRepository", "PlayerRepository"]

