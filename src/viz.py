"""Gráficos de scouting: perfil em barras de percentil, comparação e dispersão."""
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from src.similarity import LABELS, percentiles

# Métricas exibidas no perfil, agrupadas por fase do jogo
PROFILE_METRICS = {
    "Ataque": ["np_xg_p90", "np_shots_p90", "touches_box_p90"],
    "Criação": ["xa_p90", "key_passes_p90", "passes_into_box_p90"],
    "Progressão": ["prog_passes_p90", "prog_carries_p90", "dribbles_completed_p90"],
    "Defesa": ["tackles_won_p90", "interceptions_p90", "pressures_p90"],
}
SLICE_COLORS = {"Ataque": "#2a78d6", "Criação": "#1d9e75", "Progressão": "#e09b2d", "Defesa": "#c2410c"}
BG, TEXT = "#f8f7f4", "#1f2328"


def _metric_lists():
    metrics, colors = [], []
    for block, cols in PROFILE_METRICS.items():
        metrics += cols
        colors += [SLICE_COLORS[block]] * len(cols)
    return metrics, colors


def _pct_row(pool_df: pd.DataFrame, player: str, metrics):
    pct = percentiles(pool_df)
    idx = pool_df.index[pool_df["player"] == player][0]
    return [int(pct.loc[idx, m]) for m in metrics]


def percentile_bars(pool_df: pd.DataFrame, player: str, save: str | None = None,
                    credit: str = "André Casemiro"):
    """Relatório de scouting: barras horizontais de percentil por métrica,
    agrupadas por fase do jogo, com o valor por 90 minutos ao lado."""
    metrics, colors = _metric_lists()
    pcts = _pct_row(pool_df, player, metrics)
    row = pool_df[pool_df["player"] == player].iloc[0]

    fig, ax = plt.subplots(figsize=(9, 7.4), facecolor=BG)
    ax.set_facecolor(BG)

    # posições no eixo y com um espaço entre os blocos
    ys, y, block_pos = [], 0, {}
    for block, cols in PROFILE_METRICS.items():
        block_pos[block] = y
        for _ in cols:
            ys.append(y); y += 1
        y += 0.8
    ys = [y - 1.8 - v for v in ys]  # de cima para baixo

    ax.barh(ys, [100] * len(ys), color="#e7e5df", height=0.68, zorder=0)
    ax.barh(ys, pcts, color=colors, height=0.68, zorder=1)
    ax.axvline(50, color="#8b949e", lw=1, ls="--", zorder=2)

    for yi, m, p, c in zip(ys, metrics, pcts, colors):
        ax.text(-2, yi, LABELS[m], ha="right", va="center", size=10.5, color=TEXT)
        inside = p >= 14
        ax.text(p - 1.5 if inside else p + 1.5, yi, f"{p}", ha="right" if inside else "left",
                va="center", size=10, weight="bold", color="white" if inside else c, zorder=3)
        val = row[m]
        ax.text(103, yi, f"{val:.2f}", ha="left", va="center", size=10, color="#57606a")

    for block, cols in PROFILE_METRICS.items():
        first = ys[metrics.index(cols[0])]
        ax.text(-2, first + 0.85, block.upper(), ha="right", va="center", size=9.5,
                weight="bold", color=SLICE_COLORS[block])

    ax.text(103, max(ys) + 0.85, "por 90", ha="left", va="center", size=9, color="#8b949e")
    ax.set_xlim(0, 112)
    ax.set_ylim(min(ys) - 0.7, max(ys) + 1.4)
    ax.set_yticks([]); ax.set_xticks([0, 25, 50, 75, 100])
    ax.tick_params(axis="x", colors="#8b949e", labelsize=9)
    for s_ in ("top", "right", "left", "bottom"):
        ax.spines[s_].set_visible(False)

    fig.text(0.02, 0.965, f"{row['player']} ({row['team']})", size=17, weight="bold", color=TEXT)
    fig.text(0.02, 0.93, f"{row['position']} · {row['minutes']} min · percentil vs. {len(pool_df)} "
             f"jogadores da posição (≥ 270 min)", size=10.5, color="#57606a")
    fig.text(0.98, 0.012, f"Dados: StatsBomb Open Data · {credit}", ha="right", size=8.5, color="#8b949e")
    fig.subplots_adjust(left=0.27, right=0.95, top=0.89, bottom=0.06)
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
