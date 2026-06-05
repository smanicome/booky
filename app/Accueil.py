import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data.queries import get_sector_dashboard, get_time_series
from data.constants import SECTOR_AGGREGATES
from data.styles import inject_css, render_header, get_page_icon

st.set_page_config(
    page_title="Booky",
    layout="wide",
    page_icon=get_page_icon(),
)
inject_css()
render_header()

st.title("Indices de Chiffres d'Affaires — France")
st.caption(
    "Indices mensuels de chiffres d'affaires (base 2021) couvrant l'industrie, la construction, "
    "le commerce et les services. Source : INSEE · Données CVS-CJO."
)

with st.expander("Comprendre ces indicateurs"):
    st.markdown("""
**Qu'est-ce qu'un indice de chiffre d'affaires ?**

Un indice de chiffre d'affaires (ICA) mesure l'évolution des recettes perçues par les entreprises d'un secteur, par rapport à une année de référence. Publié chaque mois par l'INSEE, il permet de suivre si l'activité économique progresse, stagne ou recule.

**Comment lire les valeurs (base 2021 = 100) ?**

Toutes les valeurs sont exprimées par rapport à la moyenne de l'année 2021, fixée arbitrairement à 100.
- Un indice de **110** signifie que le chiffre d'affaires est **10 % supérieur** à celui de 2021.
- Un indice de **90** signifie qu'il est **10 % inférieur** à celui de 2021.

**Qu'est-ce que le CVS-CJO ?**

Les données brutes sont affectées par des effets mécaniques qui masquent la tendance réelle :
- les **variations saisonnières** : le commerce est naturellement plus fort en décembre (fêtes) et plus faible en août (vacances) — ces hausses et baisses se répètent chaque année et ne reflètent pas une vraie dynamique économique.
- les **jours ouvrables** : un mois comportant plus de jours travaillés produit mécaniquement plus de chiffre d'affaires qu'un mois plus court.

La correction **CVS-CJO** (Corrigé des Variations Saisonnières et des Jours Ouvrables) neutralise ces deux effets pour ne garder que le signal économique de fond.

**Variation mensuelle vs variation annuelle**

- La **variation mensuelle** compare le mois en cours au mois précédent. Elle est utile pour détecter un retournement rapide, mais peut être volatile.
- La **variation annuelle** compare le mois en cours au même mois de l'année précédente. Plus stable, elle élimine les effets saisonniers résiduels et donne une vision plus fiable de la tendance.

**Les quatre secteurs**

| Secteur | Ce qu'il couvre |
|---|---|
| Industrie manufacturière | Fabrication de biens : agroalimentaire, automobile, chimie, métallurgie, textile… |
| Construction | Bâtiment (logements, bureaux) et travaux publics (routes, réseaux) |
| Commerce | Vente en gros et au détail, réparation automobile |
| Services | Transport, hébergement, restauration, services aux entreprises, activités culturelles… |
""")

st.divider()

with st.spinner("Chargement des données..."):
    df = get_sector_dashboard()

if df.empty:
    st.error("Impossible de charger les données. Vérifiez la configuration S3.")
    st.stop()

# KPI cards
st.caption(
    "Dernières valeurs disponibles, corrigées des variations saisonnières et des jours ouvrables (CVS-CJO). "
    "La flèche indique la variation par rapport au même mois de l'année précédente. "
    "Cliquez sur le (?) pour voir le détail mensuel."
)
cols = st.columns(len(df))
for col, (_, row) in zip(cols, df.iterrows()):
    mom = row["Variation mensuelle (%)"]
    yoy = row["Variation annuelle (%)"]
    offset = row["Indice (base 2021)"] - 100
    mom_line = f"Variation mensuelle : {mom:+.2f}% (par rapport au mois précédent)." if pd.notna(mom) else ""
    col.metric(
        label=row["Secteur"],
        value=f"{row['Indice (base 2021)']:.1f} pts",
        delta=f"{yoy:+.1f}% /an" if pd.notna(yoy) else None,
        help=(
            f"Période : {row['Période']}. "
            f"Une valeur de {row['Indice (base 2021)']:.1f} signifie que le chiffre d'affaires est "
            f"{offset:+.1f}% par rapport au niveau moyen de 2021. "
            f"{mom_line}"
        ),
    )

st.divider()

# YoY bar chart
st.subheader("Variation annuelle par secteur (%)")
fig = px.bar(
    df.dropna(subset=["Variation annuelle (%)"]),
    x="Secteur",
    y="Variation annuelle (%)",
    color="Variation annuelle (%)",
    color_continuous_scale=["#d62728", "#aec7e8", "#1f77b4"],
    color_continuous_midpoint=0,
    text="Variation annuelle (%)",
)
fig.update_traces(texttemplate="%{text:+.1f}%", textposition="outside")
fig.update_layout(
    coloraxis_showscale=False,
    yaxis_title="Variation (%)",
    xaxis_title=None,
    margin=dict(t=20, b=0),
    height=350,
)
st.plotly_chart(fig, width="stretch")
st.caption(
    "Variation du chiffre d'affaires entre le dernier mois disponible et le même mois un an plus tôt. "
    "Bleu = hausse, rouge = recul. Un secteur absent manque de données sur les 12 derniers mois."
)

st.subheader("Tableau récapitulatif")
display = df[["Secteur", "Période", "Indice (base 2021)", "Variation mensuelle (%)", "Variation annuelle (%)"]].copy()
display = display.rename(columns={"Indice (base 2021)": "Indice (pts)"})
st.dataframe(
    display.style.format(
        {
            "Indice (pts)": "{:.2f}",
            "Variation mensuelle (%)": "{:+.2f}%",
            "Variation annuelle (%)": "{:+.2f}%",
        },
        na_rep="—",
    ).map(
        lambda v: "color: #d62728" if isinstance(v, float) and v < 0 else ("color: #2ca02c" if isinstance(v, float) and v > 0 else ""),
        subset=["Variation mensuelle (%)", "Variation annuelle (%)"],
    ),
    width="stretch",
    hide_index=True,
)
st.caption(
    "Période : mois de la dernière publication disponible, qui peut varier selon les secteurs. "
    "Variation mensuelle : évolution par rapport au mois précédent. "
    "Variation annuelle : évolution par rapport au même mois de l'année passée. "
    "— indique que la donnée est absente ou trop ancienne pour être calculée."
)

st.divider()

# Sector trend overview
st.subheader("Évolution des indices par secteur (CVS-CJO)")

traces = []
for sector, (activity, idx_type) in SECTOR_AGGREGATES.items():
    ts = get_time_series(activity, idx_type, "Y")
    if not ts.empty:
        traces.append(go.Scatter(
            x=ts["TIME_PERIOD"],
            y=ts["OBS_VALUE"],
            name=sector,
            mode="lines",
            hovertemplate="%{x|%b %Y}: <b>%{y:.1f} pts</b><extra>" + sector + "</extra>",
        ))

fig2 = go.Figure(traces)
fig2.add_hline(y=100, line_dash="dot", line_color="grey", annotation_text="Base 2021 = 100", annotation_position="bottom right")
fig2.update_layout(
    xaxis_title=None,
    yaxis_title="Indice (base 2021 = 100)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(t=40, b=0),
    height=420,
    hovermode="x unified",
)
st.plotly_chart(fig2, width="stretch")
st.caption(
    "Chaque courbe retrace l'évolution mensuelle du chiffre d'affaires de son secteur depuis le début de la série. "
    "La ligne pointillée à 100 représente le niveau moyen de 2021 : au-dessus, le secteur dépasse son activité de référence ; "
    "en dessous, il est en deçà. Les séries sont corrigées des variations saisonnières (CVS-CJO)."
)
