"""Ponto de entrada de compatibilidade na raiz do repositório.

Delega diretamente para a aplicação modular em ``src/sbmm/app.py`` para que tanto
``streamlit run app_demo.py`` quanto ``run dev`` executem a mesma interface.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from sbmm.app import main  # noqa: E402

main()
