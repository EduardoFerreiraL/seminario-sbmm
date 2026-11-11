"""Ponto de entrada do dashboard Streamlit.

Uso:
    streamlit run src/sbmm/app.py      (ou: run dev)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permite `streamlit run src/sbmm/app.py` mesmo sem `pip install -e .`
_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

from sbmm.controllers.matchmaking_controller import get_controller  # noqa: E402
from sbmm.infra.logging_config import setup_logging  # noqa: E402
from sbmm.views import header, styles  # noqa: E402


def main() -> None:
    setup_logging()
    st.set_page_config(page_title="SBMM In-Database ML - LoL", page_icon="🎮", layout="wide")
    styles.inject_global_styles()
    header.render()
    controller = get_controller()
    if controller is not None:
        controller.run()


main()

