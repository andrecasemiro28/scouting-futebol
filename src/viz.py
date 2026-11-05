"""Gráficos de scouting: pizza de percentis e comparação entre dois jogadores."""
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from mplsoccer import PyPizza

from src.similarity import LABELS, percentiles

# Métricas exibidas na pizza, agrupadas por fase do jogo
PIZZA_METRICS = {
    "Ataque": ["np_xg_p90", "np_shots_p90", "touches_box_p90"],
    "Criação": ["xa_p90", "key_passes_p90", "passes_into_box_p90"],
    "Progressão": ["prog_passes_p90", "prog_carries_p90", "dribbles_completed_p90"],
    "Defesa": ["tackles_won_p90", "interceptions_p90", "pressures_p90"],
}
SLICE_COLORS = {"Ataque": "#2a78d6", "Criação": "#1d9e75", "Progressão": "#e09b2d", "Defesa": "#c2410c"}
BG, TEXT = "#f8f7f4", "#1f2328"


def _metric_lists():
    metrics, colors = [], []
    for block, cols in PIZZA_METRICS.items():
        metrics += cols
        colors += [SLICE_COLORS[block]] * len(cols)
    return metrics, colors


def _pct_row(pool_df: pd.DataFrame, player: str, metrics):
    pct = percentiles(pool_df)
    idx = pool_df.index[pool_df["player"] == player][0]
    return [int(pct.loc[idx, m]) for m in metrics]


def pizza(pool_df: pd.DataFrame, player: str, subtitle: str = "", save: str | None = None,
          credit: str = "André Casemiro"):
    """Pizza de percentis de um jogador contra o grupo de comparação."""
    metrics, colors = _metric_lists()
    values = _pct_row(pool_df, player, metrics)
    row = pool_df[pool_df["player"] == player].iloc[0]

    baker = PyPizza(params=[LABELS[m] for m in metrics], background_color=BG,
                    straight_line_color="#d0d0d0", last_circle_color="#bbbbbb",
                    other_circle_color="#e2e2e2", other_circle_ls="--", inner_circle_size=18)
    fig, ax = baker.make_pizza(
        values, figsize=(8, 8.6), color_blank_space="same", blank_alpha=0.25,
        slice_colors=colors, value_colors=["white"] * len(values),
        value_bck_colors=colors, param_location=110,
        kwargs_slices=dict(edgecolor=BG, zorder=2, linewidth=1.5),
        kwargs_params=dict(color=TEXT, fontsize=10),
        kwargs_values=dict(color="white", fontsize=10, zorder=3,
                           bbox=dict(edgecolor="none", boxstyle="round,pad=0.25", lw=0)),
    )
    fig.text(0.5, 0.975, f"{row['player']} ({row['team']})", ha="center", size=17, weight="bold", color=TEXT)
    fig.text(0.5, 0.945, subtitle or f"{row['minutes']} min · percentis vs. {len(pool_df)} jogadores da posição",
             ha="center", size=10.5, color="#57606a")
    x = 0.2
    for block, c in SLICE_COLORS.items():
        fig.text(x, 0.915, f"■ {block}", color=c, size=10.5, weight="bold"); x += 0.16
    fig.text(0.5, 0.02, f"Dados: StatsBomb Open Data · Métricas por 90 minutos · {credit}",
             ha="center", size=8.5, color="#8b949e")
    if save:
        fig.savefig(save, dpi=160, bbox_inches="tight", facecolor=BG)
    return fig


def compare_bars(pool_df: pd.DataFrame, player_a: str, player_b: str, save: str | None = None):
    """Compara os percentis de dois jogadores métrica a métrica (gráfico de halteres)."""
    metrics, colors = _metric_lists()
    va, vb = _pct_row(pool_df, player_a, metrics), _pct_row(pool_df, player_b, metrics)
    ca, cb = "#2a78d6", "#e0662d"
    labels = [LABELS[m] for m in metrics][::-1]
    va, vb, colors = va[::-1], vb[::-1], colors[::-1]
    y = range(len(metrics))

    fig, ax = plt.subplots(figsize=(8.5, 7), facecolor=BG)
    ax.set_facecolor(BG)
    for i in y:
        ax.plot([va[i], vb[i]], [i, i], color="#c9ced6", lw=3, zorder=1)
    ax.scatter(va, y, s=110, color=ca, zorder=2, label=player_a)
    ax.scatter(vb, y, s=110, color=cb, zorder=2, label=player_b)
    ax.set_yticks(list(y), labels, color=TEXT)
    for tick, c in zip(ax.get_yticklabels(), colors):
        tick.set_color(c); tick.set_fontweight("bold")
    ax.set_xlim(0, 102)
    ax.set_xlabel("Percentil vs. jogadores da posição", color=TEXT)
    ax.grid(axis="x", color="#e2e2e2", ls="--")
    for s_ in ("top", "right", "left"):
        ax.spines[s_].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title(f"{player_a} vs. {player_b}", loc="left", size=14, weight="bold", color=TEXT, pad=28)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=10)
    fig.text(0.98, 0.01, "Dados: StatsBomb Open Data", ha="right", size=8.5, color="#8b949e")
    fig.tight_layout()
    if save:
        fig.savefig(save, dpi=160, bbox_inches="tight", facecolor=BG)
    return fig


def scatter_finishing(pool_df: pd.DataFrame, highlight: int = 8, save: str | None = None):
    """xG sem pênalti/90 vs. gols - xG: quem gera chances e quem converte acima do esperado."""
    d = pool_df.assign(diff=pool_df["np_goals"] - pool_df["np_xg"])
    fig, ax = plt.subplots(figsize=(9, 6.5), facecolor=BG)
    ax.set_facecolor(BG)
    ax.scatter(d["np_xg_p90"], d["diff"], s=d["minutes"] / 6, color="#2a78d6", alpha=0.45, edgecolor="white")
    ax.axhline(0, color="#8b949e", lw=1, ls="--")
    top = pd.concat([d.nlargest(highlight, "np_xg_p90"), d.nlargest(3, "diff"), d.nsmallest(3, "diff")]).drop_duplicates("player_id")
    for _, r in top.iterrows():
        ax.annotate(r["player"], (r["np_xg_p90"], r["diff"]), xytext=(5, 4), textcoords="offset points", size=9, color=TEXT)
    ax.set_xlabel("xG sem pênalti por 90 min (volume de chances)", color=TEXT)
    ax.set_ylabel("Gols sem pênalti − xG (eficiência)", color=TEXT)
    ax.set_title("Centroavantes: geração de chances vs. conversão", loc="left", size=14, weight="bold", color=TEXT)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.text(1, -0.14, "Tamanho do ponto = minutos jogados · Dados: StatsBomb Open Data",
            transform=ax.transAxes, ha="right", size=8.5, color="#8b949e")
    fig.tight_layout()
    if save:
        fig.savefig(save, dpi=160, bbox_inches="tight", facecolor=BG)
    return fig
