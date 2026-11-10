"""Leitura e validação centralizada das variáveis de ambiente (.env).

Nenhum outro módulo deve chamar ``os.getenv`` diretamente: tudo passa por ``Settings``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from dotenv import load_dotenv

from sbmm.domain.errors import ConfigError

_FALSE_VALUES = {"false", "0", "no", "nao", "não", "off"}


def _mask(secret: str | None) -> str:
    """Mascara um segredo para exibição segura em logs/tracebacks."""
    if not secret:
        return "<vazio>"
    return f"{secret[:6]}…({len(secret)} chars)"


@dataclass(frozen=True)
class Settings:
    """Configuração imutável da aplicação."""

    supabase_url: str
    supabase_key: str = field(repr=False)
    service_key: str | None = field(default=None, repr=False)
    verify_ssl: bool = True
    ca_bundle: str | None = None
    request_timeout: float = 10.0

    def __repr__(self) -> str:  # nunca expõe as chaves
        return (
            f"Settings(supabase_url={self.supabase_url!r}, supabase_key={_mask(self.supabase_key)}, "
            f"service_key={_mask(self.service_key)}, verify_ssl={self.verify_ssl}, "
            f"ca_bundle={self.ca_bundle!r}, request_timeout={self.request_timeout})"
        )

    __str__ = __repr__

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None, *, load_file: bool = True) -> Settings:
        """Constrói as configurações a partir do ambiente (ou de um dicionário, nos testes)."""
        if env is None:
            if load_file:
                load_dotenv()
            env = os.environ

        url = (env.get("SUPABASE_URL") or "").strip()
        key = (env.get("SUPABASE_KEY") or "").strip()
        if not url or not key:
            raise ConfigError("Defina SUPABASE_URL e SUPABASE_KEY no arquivo .env (veja .env.example).")
        if not url.startswith("https://"):
            raise ConfigError("SUPABASE_URL deve começar com https://")

        ca_bundle = (env.get("SUPABASE_CA_BUNDLE") or "").strip() or None
        if ca_bundle and not os.path.isfile(ca_bundle):
            raise ConfigError(f"SUPABASE_CA_BUNDLE aponta para um arquivo inexistente: {ca_bundle}")

        raw_timeout = (env.get("SUPABASE_TIMEOUT") or "10").strip()
        try:
            timeout = float(raw_timeout)
        except ValueError as exc:
            raise ConfigError(f"SUPABASE_TIMEOUT inválido: {raw_timeout!r}") from exc
        if timeout <= 0:
            raise ConfigError("SUPABASE_TIMEOUT deve ser maior que zero.")

        return cls(
            supabase_url=url.rstrip("/"),
            supabase_key=key,
            service_key=(env.get("SUPABASE_SERVICE_KEY") or "").strip() or None,
            verify_ssl=(env.get("SUPABASE_VERIFY_SSL") or "true").strip().lower() not in _FALSE_VALUES,
            ca_bundle=ca_bundle,
            request_timeout=timeout,
        )

    def require_service_key(self) -> str:
        """Chave de escrita (secret/service_role). Usada SOMENTE por scripts administrativos."""
        if not self.service_key:
            raise ConfigError(
                "SUPABASE_SERVICE_KEY não definida. Scripts de escrita (seed) exigem a chave secreta "
                "(Project Settings → API Keys → sb_secret_...). Nunca use essa chave no dashboard."
            )
        return self.service_key

