import sys
from pathlib import Path
import streamlit as st
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.queries import get_commerce_value_vs_volume, get_available_activities
from data.connection import get_metadata
from data.styles import inject_css, render_header, get_page_icon

st.set_page_config(page_title="Booky", layout="wide", page_icon=get_page_icon())
inject_css()
render_header()
st.title("Commerce — Valeur vs Volume des ventes")
st.caption(
    "Comparaison entre l'indice de chiffre d'affaires (valeur courante) et l'indice de volume des ventes "
    "(IVVC, déflaté). L'écart entre les deux reflète l'effet prix. CVS-CJO · Base 2021 = 100."
)

metadata = get_metadata()
activity_labels: dict[str, str] = metadata.get("ACTIVITY", {})

with st.spinner("Chargement des activités..."):
    acts_df = get_available_activities("ICA_COMM")

act_options = [str(a) for a in acts_df["ACTIVITY"]]
act_labels = {a: f"{a} — {activity_labels.get(a, a)}" for a in act_options}

with st.sidebar:
    st.header("Filtres")
    with st.expander("Comprendre cette page"):
        st.markdown("""
**Valeur vs volume : quelle différence ?**

Un chiffre d'affaires peut augmenter pour deux raisons très différentes :
1. **Les entreprises vendent plus de produits** → hausse des volumes.
2. **Les entreprises vendent aux mêmes volumes mais à des prix plus élevés** → hausse des prix.

Pour distinguer ces deux effets, l'INSEE publie deux indices :
- **Indice de valeur (ICA_COMM)** : mesure l'évolution du chiffre d'affaires en euros courants, sans correction des prix. Il reflète ce que les entreprises ont réellement encaissé.
- **Indice de volume des ventes (IVVC)** : mesure l'évolution des quantités vendues après avoir retiré l'effet des prix (on parle d'indice "déflaté"). Il répond à la question : *est-ce qu'on vend vraiment plus ?*

**L'effet prix**

L'écart entre les deux courbes représente la part de la croissance du chiffre d'affaires qui est uniquement due aux variations de prix.
- **Effet prix positif** : les prix ont augmenté plus vite que les volumes — la croissance est en partie "artificielle" (inflation).
- **Effet prix négatif** : les prix ont baissé (déflation, promotions) — l'entreprise vend plus de produits mais encaisse moins par unité.

Un secteur où valeur et volume évoluent en parallèle est un secteur dont la croissance est saine et tirée par une vraie demande.
""")

    default_idx = next((i for i, a in enumerate(act_options) if a == "G"), 0)
    activity = st.selectbox(
        "Activité commerciale",
        options=act_options,
        index=default_idx,
        format_func=lambda k: act_labels[k],
        help=(
            "Activité du secteur commerce (NAF section G). "
            "Seules les activités disposant à la fois d'un indice de valeur (ICA_COMM) "
            "et d'un indice de volume (IVVC) sont comparables ici."
        ),
    )
    show_gap = st.checkbox(
        "Afficher l'effet prix (Valeur − Volume)",
        value=True,
        help=(
            "Affiche un graphique en barres représentant l'écart entre la croissance en valeur "
            "et la croissance en volume. Positif = l'inflation contribue à la hausse du CA. "
            "Négatif = les prix baissent malgré des volumes en hausse."
        ),
    )

with st.spinner("Chargement des données..."):
    df = get_commerce_value_vs_volume(activity)

if df.empty:
    st.warning("Aucune donnée disponible pour cette activité.")
    st.stop()

label = activity_labels.get(activity, activity)
st.subheader(f"{label} ({activity})")

# Align on common time periods
pivot = df.pivot(index="TIME_PERIOD", columns="IDX_TYPE", values="OBS_VALUE").dropna()

fig = go.Figure()
colors = {"Valeur (CA)": "#1f77b4", "Volume des ventes": "#ff7f0e"}
for col in pivot.columns:
    fig.add_trace(go.Scatter(
        x=pivot.index,
        y=pivot[col],
        name=col,
        mode="lines",
        line=dict(width=2, color=colors.get(col)),
        hovertemplate="%{x|%b %Y}: <b>%{y:.2f} pts</b><extra>" + col + "</extra>",
    ))

fig.add_hline(y=100, line_dash="dot", line_color="grey", annotation_text="Base 2021 = 100")
fig.update_layout(
    xaxis_title=None,
    yaxis_title="Indice (base 2021 = 100)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    hovermode="x unified",
    height=420,
    margin=dict(t=40, b=0),
)
st.plotly_chart(fig, width="stretch")
st.caption(
    "Valeur (bleu) : chiffre d'affaires en euros courants — reflète ce que les entreprises encaissent réellement. "
    "Volume (orange) : quantités vendues après retrait de l'effet des prix. "
    "Si les deux courbes évoluent en parallèle, la croissance est tirée par les volumes (saine). "
    "Un écart croissant entre les deux signale une croissance portée par les prix (effet inflationniste)."
)

if show_gap and "Valeur (CA)" in pivot.columns and "Volume des ventes" in pivot.columns:
    pivot["Effet prix"] = pivot["Valeur (CA)"] - pivot["Volume des ventes"]

    st.subheader("Effet prix (Valeur − Volume)")
    st.caption(
        "Mesure l'écart en points d'indice entre la croissance en valeur et la croissance en volume. "
        "Barre rouge (positif) : les prix ont augmenté plus vite que les volumes — la hausse du CA est en partie due à l'inflation. "
        "Barre bleue (négatif) : les prix ont baissé ou des promotions ont réduit la valeur unitaire, "
        "malgré des volumes potentiellement en hausse."
    )

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=pivot.index,
        y=pivot["Effet prix"],
        marker_color=pivot["Effet prix"].apply(lambda v: "#d62728" if v >= 0 else "#1f77b4"),
        hovertemplate="%{x|%b %Y}: <b>%{y:+.2f}</b> pts<extra></extra>",
        name="Effet prix",
    ))
    fig2.add_hline(y=0, line_color="grey")
    fig2.update_layout(
        yaxis_title="Points d'indice",
        xaxis_title=None,
        height=280,
        margin=dict(t=10, b=0),
        showlegend=False,
    )
    st.plotly_chart(fig2, width="stretch")

st.divider()

latest_period = pivot.index.max()
latest = pivot.loc[latest_period]

st.caption(f"Dernières valeurs disponibles — {latest_period.strftime('%B %Y')}.")

_idx_help = {
    "Valeur (CA)": (
        "Indice de chiffre d'affaires en valeur courante (ICA_COMM, base 2021 = 100). "
        "Mesure l'évolution des recettes en euros, sans correction des prix."
    ),
    "Volume des ventes": (
        "Indice de volume des ventes (IVVC, base 2021 = 100), déflaté pour retirer l'effet des prix. "
        "Répond à la question : vend-on plus ou moins de produits qu'en 2021 ?"
    ),
}

cols = st.columns(len(latest) - (1 if "Effet prix" in latest.index else 0))
col_iter = iter(cols)
for name, val in latest.items():
    if name == "Effet prix":
        continue
    next(col_iter).metric(name, f"{val:.2f} pts", f"{latest_period.strftime('%b %Y')}", help=_idx_help.get(name))

st.divider()
with st.expander("Données tabulaires"):
    st.caption("Valeurs mensuelles des deux indices (base 2021 = 100). L'Effet prix est calculé comme Valeur − Volume.")
    display = pivot.copy()
    display.index = display.index.strftime("%Y-%m")
    st.dataframe(
        display.sort_index(ascending=False).style.format("{:.2f}", na_rep="—"),
        width="stretch",
        height=350,
    )
