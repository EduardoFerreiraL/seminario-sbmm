"""Fábrica do client Supabase com TLS verificado e timeout."""

from __future__ import annotations

import logging

import httpx
from supabase import Client, ClientOptions, create_client

from sbmm.config.settings import Settings

log = logging.getLogger(__name__)


def _ssl_verify(settings: Settings) -> str | bool:
    """CA customizada (proxy corporativo) > verificação padrão > desligado (só se explícito)."""
    if settings.ca_bundle:
        return settings.ca_bundle
    if not settings.verify_ssl:
        log.warning(
            "Verificação SSL DESLIGADA (SUPABASE_VERIFY_SSL=false). Use apenas em desenvolvimento; "
            "prefira SUPABASE_CA_BUNDLE apontando para o certificado do proxy."
        )
        return False
    return True


def create_supabase(settings: Settings, *, use_service_key: bool = False) -> Client:
    """Cria o client. ``use_service_key=True`` só deve ser usado por scripts administrativos."""
    key = settings.require_service_key() if use_service_key else settings.supabase_key
    http = httpx.Client(verify=_ssl_verify(settings), timeout=settings.request_timeout)
    log.info("Conectando ao Supabase em %s (chave %s)", settings.supabase_url,
             "de serviço" if use_service_key else "pública")
    return create_client(settings.supabase_url, key, options=ClientOptions(httpx_client=http))

