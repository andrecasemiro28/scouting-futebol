"""Busca de jogadores similares (perfil estatístico por 90 minutos)."""
from __future__ import annotations

import numpy as np
import pandas as pd

# Métricas usadas para definir o "estilo" do jogador
FEATURES = [
    "np_xg_p90", "np_shots_p90", "touches_box_p90",            # finalização
    "xa_p90", "key_passes_p90", "passes_into_box_p90",         # criação
    "prog_passes_p90", "prog_carries_p90", "carries_into_box_p90",
    "dribbles_completed_p90", "crosses_completed_p90",         # progressão / 1x1
    "passes_p90", "pass_pct", "turnovers_p90",                 # retenção de posse
    "tackles_won_p90", "interceptions_p90", "recoveries_p90",
    "pressures_p90", "pressures_att_third_p90",                # defesa / pressão
]

LABELS = {
    "np_xg_p90": "xG sem pênalti", "np_shots_p90": "Finalizações", "touches_box_p90": "Toques na área",
    "xa_p90": "xA", "key_passes_p90": "Passes-chave", "passes_into_box_p90": "Passes p/ área",
    "prog_passes_p90": "Passes progressivos", "prog_carries_p90": "Conduções progressivas",
    "carries_into_box_p90": "Conduções p/ área", "dribbles_completed_p90": "Dribles certos",
    "crosses_completed_p90": "Cruzamentos certos", "passes_p90": "Passes tentados",
    "pass_pct": "% passes certos", "turnovers_p90": "Perdas de posse",
    "tackles_won_p90": "Desarmes", "interceptions_p90": "Interceptações",
    "recoveries_p90": "Recuperações", "pressures_p90": "Pressões",
    "pressures_att_third_p90": "Pressões no ataque", "np_goals_p90": "Gols sem pênalti",
}


def pool(df: pd.DataFrame, groups: list[str], min_minutes: int = 270) -> pd.DataFrame:
    """Jogadores das posições escolhidas com minutagem mínima."""
    return df[df["group"].isin(groups) & (df["minutes"] >= min_minutes)].copy()


def percentiles(pool_df: pd.DataFrame, cols=FEATURES) -> pd.DataFrame:
    """Percentil (0-100) de cada métrica dentro do grupo de comparação.
    Para perdas de posse, menor é melhor, então o percentil é invertido."""
    pct = pool_df[cols].rank(pct=True) * 100
    if "turnovers_p90" in pct:
        pct["turnovers_p90"] = 100 - pct["turnovers_p90"] + 100 / len(pool_df)
    return pct.round(0)


def find_similar(df: pd.DataFrame, player: str, groups: list[str] | None = None,
                 min_minutes: int = 270, n: int = 10, features=FEATURES) -> pd.DataFrame:
    """Top-n jogadores mais parecidos com `player` (similaridade de cosseno
    sobre métricas padronizadas por z-score dentro do grupo de posições)."""
    target = df[df["player"] == player]
    if target.empty:
        raise ValueError(f"Jogador não encontrado: {player}")
    target = target.iloc[0]
    groups = groups or [target["group"]]

    p = pool(df, groups, min_minutes)
    if target["player_id"] not in set(p["player_id"]):
        p = pd.concat([p, target.to_frame().T])

    X = p[features].astype(float)
    Z = (X - X.mean()) / X.std(ddof=0).replace(0, 1)
    t = Z[p["player_id"] == target["player_id"]].iloc[0].to_numpy()
    sims = (Z.to_numpy() @ t) / (np.linalg.norm(Z.to_numpy(), axis=1) * np.linalg.norm(t))

    out = p.assign(similarity=(sims * 100).round(1))
    out = out[out["player_id"] != target["player_id"]]
    cols = ["player", "team", "position", "minutes", "similarity"]
    return out.sort_values("similarity", ascending=False)[cols].head(n).reset_index(drop=True)
