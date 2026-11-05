"""App de scouting: perfil, jogadores similares e lista curta por filtros.

Rodar localmente:  streamlit run app.py
"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from src import viz
from src.similarity import FEATURES, LABELS, find_similar, percentiles, pool

st.set_page_config(page_title="Scouting por similaridade", page_icon="⚽", layout="wide")

GROUPS = {"Ponta": "PON", "Centroavante": "ATA", "Meia": "MEI", "Volante": "VOL",
          "Lateral": "LAT", "Zagueiro": "ZAG"}
LABELS_ALL = {**LABELS, "np_goals_p90": "Gols sem pênalti", "minutes": "Minutos"}


@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_csv(Path(__file__).parent / "data" / "processed" / "player_stats.csv")


df = load_data()

# ---------------- barra lateral ----------------
st.sidebar.title("⚽ Scouting")
st.sidebar.caption("Copa 2022 · Euro 2024 · Copa América 2024 · Copa Africana 2023")
pos_name = st.sidebar.selectbox("Posição", list(GROUPS), index=0)
group = GROUPS[pos_name]
min_minutes = st.sidebar.slider("Minutos mínimos", 90, 900, 270, step=45,
                                help="Corte para evitar amostras pequenas nas métricas por 90.")
pos_pool = pool(df, [group], min_minutes)
if len(pos_pool) < 5:
    st.warning("Poucos jogadores com esse corte de minutos. Diminua o filtro.")
    st.stop()

players = pos_pool.sort_values("minutes", ascending=False)["player"].tolist()
default = "Vinícius Júnior" if "Vinícius Júnior" in players else players[0]
player = st.sidebar.selectbox("Jogador", players, index=players.index(default))
st.sidebar.markdown("---")
st.sidebar.caption("Dados: [StatsBomb Open Data](https://github.com/statsbomb/open-data) · "
                   "Código: [GitHub](https://github.com/andrecasemiro28/scouting-futebol)")

row = pos_pool[pos_pool["player"] == player].iloc[0]

# ---------------- cabeçalho ----------------
st.title(f"{row['player']}")
st.caption(f"{row['team']} · {row['position']} · {row['competitions']}")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Minutos", f"{row['minutes']:,}".replace(",", "."))
c2.metric("Jogos", int(row["matches"]))
c3.metric("Gols (sem pên.)", int(row["np_goals"]))
c4.metric("xG sem pênalti", f"{row['np_xg']:.2f}")
c5.metric("xA", f"{row['xa']:.2f}")

tab_perfil, tab_sim, tab_filtro, tab_disp = st.tabs(
    ["📊 Perfil", "🔎 Jogadores similares", "🎯 Lista curta por filtros", "📈 Dispersão"])

# ---------------- perfil ----------------
with tab_perfil:
    col, txt = st.columns([3, 2])
    with col:
        st.pyplot(viz.percentile_bars(pos_pool, player), width="stretch")
    with txt:
        st.subheader("Como ler")
        st.markdown(
            f"Cada barra mostra o **percentil** do jogador entre os **{len(pos_pool)} {pos_name.lower()}s** "
            f"com pelo menos {min_minutes} minutos. Percentil 90 significa que ele supera 90% da posição. "
            "À direita está o valor bruto **por 90 minutos**.")
        pct = percentiles(pos_pool).loc[row.name]
        top = pct.sort_values(ascending=False).head(3)
        low = pct.sort_values().head(3)
        st.markdown("**Pontos fortes**\n" + "\n".join(f"- {LABELS[m]}: percentil {int(v)}" for m, v in top.items()))
        st.markdown("**Pontos a desenvolver**\n" + "\n".join(f"- {LABELS[m]}: percentil {int(v)}" for m, v in low.items()))

# ---------------- similares ----------------
with tab_sim:
    n = st.slider("Quantos jogadores mostrar", 5, 20, 10)
    sims = find_similar(df, player, groups=[group], min_minutes=min_minutes, n=n)
    left, right = st.columns([1, 1])
    with left:
        st.dataframe(
            sims.drop(columns="position").rename(columns={"player": "Jogador", "team": "Seleção",
                                                          "minutes": "Minutos", "similarity": "Similaridade"}),
            hide_index=True, width="stretch",
            column_config={"Similaridade": st.column_config.ProgressColumn(
                "Similaridade", min_value=0, max_value=100, format="%.1f")})
        st.caption("Similaridade de cosseno entre métricas por 90 padronizadas (z-score) dentro da posição. "
                   "100 = perfil idêntico.")
    with right:
        other = st.selectbox("Comparar com", sims["player"].tolist())
        st.pyplot(viz.compare_bars(pos_pool, player, other), width="stretch")

# ---------------- lista curta ----------------
with tab_filtro:
    st.markdown("Escolha métricas e o **percentil mínimo** em cada uma. "
                "Útil para pedidos do tipo *'quero um volante que construa e recupere bolas'*.")
    chosen = st.multiselect("Métricas", FEATURES, default=["prog_passes_p90", "pass_pct", "recoveries_p90"],
                            format_func=lambda m: LABELS[m])
    cut = st.slider("Percentil mínimo em todas", 0, 95, 60, step=5)
    if chosen:
        pct_all = percentiles(pos_pool)
        mask = (pct_all[chosen] >= cut).all(axis=1)
        out = pos_pool[mask].copy()
        out["Score"] = pct_all.loc[mask, chosen].mean(axis=1).round(0)
        if "pass_pct" in chosen:
            out["pass_pct"] = out["pass_pct"] * 100  # exibe em %
        show = out.sort_values("Score", ascending=False)[["player", "team", "minutes", "Score"] + chosen]
        show = show.rename(columns={"player": "Jogador", "team": "Seleção", "minutes": "Minutos", **LABELS})
        st.write(f"**{len(show)} jogadores** passam no filtro.")
        st.dataframe(show.round(2), hide_index=True, width="stretch")

# ---------------- dispersão ----------------
with tab_disp:
    opts = FEATURES + ["np_goals_p90"]
    a, b = st.columns(2)
    x = a.selectbox("Eixo X", opts, index=opts.index("np_xg_p90"), format_func=lambda m: LABELS_ALL[m])
    y = b.selectbox("Eixo Y", opts, index=opts.index("xa_p90"), format_func=lambda m: LABELS_ALL[m])
    d = pos_pool.assign(destaque=pos_pool["player"].eq(player).map({True: player, False: "Outros"}))
    base = alt.Chart(d)
    points = (
        base.mark_circle(opacity=0.75)
        .encode(
            x=alt.X(x, title=LABELS_ALL[x]), y=alt.Y(y, title=LABELS_ALL[y]),
            size=alt.Size("minutes", title="Minutos", legend=None),
            color=alt.Color("destaque", scale=alt.Scale(domain=[player, "Outros"],
                                                         range=[viz.ACCENT, "#c3c8ce"]), legend=None),
            tooltip=["player", "team", "minutes", alt.Tooltip(x, format=".2f"), alt.Tooltip(y, format=".2f")],
        )
    )
    label = (base.transform_filter(alt.datum.destaque == player)
             .mark_text(align="left", dx=10, fontWeight="bold", color=viz.ACCENT)
             .encode(x=x, y=y, text="player"))
    st.altair_chart((points + label).properties(height=520).interactive(), width="stretch")
    st.caption("Passe o mouse nos pontos para ver o jogador. O jogador selecionado aparece em azul.")
