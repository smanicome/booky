import sys
from pathlib import Path
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.queries import get_market_split, get_activities_with_market_split
from data.connection import get_metadata
from data.styles import inject_css, render_header, get_page_icon

st.set_page_config(page_title="Booky", layout="wide", page_icon=get_page_icon())
inject_css()
render_header()
st.title("Marché intérieur vs Marché extérieur")
st.caption(
    "Pour l'industrie manufacturière (NAF divisions 10–33), comparaison des indices "
    "de chiffres d'affaires selon le marché de destination. CVS-CJO · Base 2021 = 100."
)

with st.expander("Comprendre cette page"):
    st.markdown("""
**Marché intérieur vs marché extérieur**

Pour l'industrie manufacturière, le chiffre d'affaires peut provenir de deux origines :
- **Marché intérieur** : ventes réalisées en France.
- **Marché extérieur** : ventes à l'export (hors de France).
- **Total** : la somme des deux.

Comparer ces deux courbes permet de comprendre si la croissance d'un secteur est tirée par la demande française ou par les exportations.

**Comment l'interpréter ?**

- Si le marché extérieur croît plus vite que l'intérieur, le secteur gagne en compétitivité à l'international.
- Si le marché intérieur progresse davantage, c'est la demande nationale qui soutient l'activité.
- Un écart qui se creuse peut signaler une divergence entre la conjoncture française et mondiale.

**Le graphique d'écart (intérieur − extérieur)**

Il mesure, en points d'indice, la différence entre les deux marchés.
- Une barre **positive** (verte) signifie que le marché intérieur est au-dessus du marché extérieur ce mois-là.
- Une barre **négative** (rouge) signifie l'inverse.
""")

metadata = get_metadata()
activity_labels: dict[str, str] = metadata.get("ACTIVITY", {})

with st.spinner("Chargement des activités..."):
    acts_df = get_activities_with_market_split()

act_options = [str(a) for a in acts_df["ACTIVITY"]]
act_labels = {a: f"{a} — {activity_labels.get(a, a)}" for a in act_options}

with st.sidebar:
    st.header("Filtres")

    default_idx = next((i for i, a in enumerate(act_options) if a == "A10_CZ"), 0)
    activity = st.selectbox(
        "Activité industrielle",
        options=act_options,
        index=default_idx,
        format_func=lambda k: act_labels[k],
        help=(
            "Seules les activités industrielles et de construction (ICA_INDCONS) disposent "
            "de la décomposition par marché de destination dans ce jeu de données."
        ),
    )
    show_gap = st.checkbox(
        "Afficher l'écart intérieur − extérieur",
        value=True,
        help=(
            "Affiche un graphique en barres montrant mois par mois si les ventes domestiques "
            "surpassent les exports (barre verte) ou l'inverse (barre rouge)."
        ),
    )

with st.spinner("Chargement des données..."):
    df = get_market_split(activity)

if df.empty:
    st.warning("Aucune donnée de décomposition marché disponible pour cette activité.")
    st.stop()

label = activity_labels.get(activity, activity)
st.subheader(f"{label} ({activity})")

# Main time series
fig = px.line(
    df,
    x="TIME_PERIOD",
    y="OBS_VALUE",
    color="MARCHE",
    color_discrete_map={
        "Total": "#1f77b4",
        "Marché intérieur": "#2ca02c",
        "Marché extérieur": "#d62728",
    },
    labels={"TIME_PERIOD": "", "OBS_VALUE": "Indice (base 2021 = 100)", "MARCHE": "Marché"},
)
fig.add_hline(y=100, line_dash="dot", line_color="grey", annotation_text="Base 2021 = 100")
fig.update_layout(
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    height=420,
    margin=dict(t=40, b=0),
)
st.plotly_chart(fig, width="stretch")
st.caption(
    "Les trois courbes évoluent autour de la base 100 (niveau moyen de 2021). "
    "Si la courbe Marché extérieur dépasse le Marché intérieur, le secteur tire sa croissance de l'export. "
    "Un écart qui se creuse peut signaler une divergence de compétitivité entre la demande nationale et internationale."
)

if show_gap:
    pivot = df.pivot(index="TIME_PERIOD", columns="MARCHE", values="OBS_VALUE").reset_index()
    if "Marché intérieur" in pivot.columns and "Marché extérieur" in pivot.columns:
        pivot["Écart (int. − ext.)"] = pivot["Marché intérieur"] - pivot["Marché extérieur"]

        st.subheader("Écart entre marché intérieur et extérieur")
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=pivot["TIME_PERIOD"],
            y=pivot["Écart (int. − ext.)"],
            marker_color=pivot["Écart (int. − ext.)"].apply(lambda v: "#2ca02c" if v >= 0 else "#d62728"),
            hovertemplate="%{x|%b %Y}: <b>%{y:+.2f}</b> pts<extra></extra>",
            name="Écart",
        ))
        fig2.add_hline(y=0, line_color="grey")
        fig2.update_layout(
            yaxis_title="Points d'indice",
            xaxis_title=None,
            height=280,
            margin=dict(t=20, b=0),
            showlegend=False,
        )
        st.plotly_chart(fig2, width="stretch")
        st.caption(
            "Écart en points d'indice entre le marché intérieur et le marché extérieur. "
            "Barre verte : les ventes domestiques surpassent les exports ce mois-là. "
            "Barre rouge : les exports surpassent les ventes domestiques. "
            "L'amplitude de la barre indique l'intensité de la divergence."
        )

st.divider()

# Summary stats for latest period
latest_period = df["TIME_PERIOD"].max()
latest = df[df["TIME_PERIOD"] == latest_period].set_index("MARCHE")["OBS_VALUE"]

st.caption(f"Dernières valeurs disponibles — {latest_period.strftime('%B %Y')}.")

_market_help = {
    "Total": (
        "Chiffre d'affaires total de l'activité, tous marchés confondus (base 2021 = 100). "
        "C'est la somme des ventes domestiques et des exports."
    ),
    "Marché intérieur": (
        "Part du chiffre d'affaires réalisée en France. "
        "Une valeur nettement supérieure à 100 indique que la demande nationale est dynamique."
    ),
    "Marché extérieur": (
        "Part du chiffre d'affaires réalisée à l'export. "
        "Une valeur en hausse signifie que le secteur gagne des parts de marché à l'international."
    ),
}

cols = st.columns(len(latest))
for col, (market, val) in zip(cols, latest.items()):
    col.metric(market, f"{val:.2f} pts", f"{latest_period.strftime('%b %Y')}", help=_market_help.get(market))

st.divider()
with st.expander("Données tabulaires"):
    st.caption("Valeurs mensuelles de l'indice (base 2021 = 100) pour chaque marché de destination. — indique une donnée absente.")
    pivot_display = df.pivot(index="TIME_PERIOD", columns="MARCHE", values="OBS_VALUE")
    pivot_display.index = pivot_display.index.strftime("%Y-%m")
    st.dataframe(
        pivot_display.sort_index(ascending=False).style.format("{:.2f}", na_rep="—"),
        width="stretch",
        height=350,
    )
