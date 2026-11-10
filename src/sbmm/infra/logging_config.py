"""Configuração padrão de logging (terminal)."""

from __future__ import annotations

import logging
import os

_CONFIGURED = False


def setup_logging(level: str | None = None) -> None:
    """Configura o logging uma única vez (o Streamlit reexecuta o script a cada interação)."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(
        level=(level or os.getenv("SBMM_LOG_LEVEL", "INFO")).upper(),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    # Bibliotecas HTTP são muito verbosas em INFO
    for noisy in ("httpx", "httpcore", "hpack"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    _CONFIGURED = True

