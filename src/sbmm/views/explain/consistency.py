"""Prova de consistência entre a explicação e o resultado da RPC."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from sbmm.domain.matchmaking import check_consistency
from sbmm.domain.models import RegressionExplain


def render(df_snake: pd.DataFrame, e: RegressionExplain, win_prob: float, origem_sgbd: bool) -> None:
    st.markdown("#### ✅ Prova de consistência")
    st.caption("Conferências automáticas que mostram que a explicação acima corresponde ao que o SGBD executou.")

    r = check_consistency(df_snake, e, win_prob)
    checks = [
        ("Snake Draft recalculado no Python gera os **mesmos times** que o SQL", r.teams_match),
        (
            f"Sigmoide aplicada ao z ({e.z:.4f}) = **{r.formula_prob:.2f}%**, igual à RPC (**{win_prob:.2f}%**)",
            r.formula_matches,
        ),
        (
            f"Probabilidade dos intermediários ({'SGBD' if origem_sgbd else 'Python'}) = **{e.prob_pct:.2f}%**, "
            f"igual à `matchmake_in_db` (**{win_prob:.2f}%**)",
            r.explain_matches,
        ),
    ]
    for txt, ok in checks:
        st.markdown(f"{'✅' if ok else '❌'} {txt}")

