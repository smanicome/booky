import sys
from pathlib import Path
import streamlit as st
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.queries import get_time_series, get_available_activities
from data.connection import get_metadata
from data.constants import IDX_TYPE_LABELS, SEASONAL_LABELS
from data.styles import inject_css, render_header, get_page_icon

st.set_page_config(page_title="Booky", layout="wide", page_icon=get_page_icon())
inject_css()
render_header()
st.title("Tendances — Exploration des séries temporelles")
st.caption("Sélectionnez un secteur, un type d'indice et une activité pour visualiser son évolution mensuelle.")

with st.expander("Comprendre cette page"):
    st.markdown("""
**Qu'est-ce qu'une série temporelle d'indice ?**

Ce graphique montre comment le chiffre d'affaires d'une activité a évolué mois après mois depuis le début de la série. La ligne horizontale en pointillés représente la base 100 (niveau moyen de 2021) : au-dessus, l'activité est plus dynamique qu'en 2021 ; en dessous, elle l'est moins.

**Types de correction saisonnière**

- **CVS-CJO** *(recommandé)* : données lissées pour éliminer les effets saisonniers et les jours ouvrables. Idéal pour analyser la tendance de fond.
- **Brut** : données telles qu'elles sont, sans correction. Les variations saisonnières sont visibles (ex. : pic annuel de décembre dans le commerce).
- **CJO uniquement** : seul l'effet du nombre de jours ouvrables est corrigé, mais pas la saisonnalité.

**L'option "Superposer brut et CVS-CJO"** permet de visualiser côte à côte la série corrigée et la série brute, pour mieux comprendre l'ampleur des effets saisonniers.

**Les statistiques en bas de page**

- *Dernière valeur* : le dernier point publié par l'INSEE pour cette activité.
- *Variation depuis début de série* : croissance totale depuis la première donnée disponible.
- *Maximum / Minimum historique* : les valeurs extrêmes atteintes sur toute la période.
""")

metadata = get_metadata()
activity_labels: dict[str, str] = metadata.get("ACTIVITY", {})


with st.sidebar:
    st.header("Filtres")

    idx_type = st.selectbox(
        "Type d'indice",
        options=list(IDX_TYPE_LABELS.keys()),
        format_func=lambda k: IDX_TYPE_LABELS[k],
        help=(
            "Détermine ce qui est mesuré : ICA = chiffre d'affaires en valeur courante (euros) ; "
            "IVVC = volume des ventes déflaté (quantités, hors effet prix) ; "
            "IPS = indice de production des services."
        ),
    )
    seasonal = st.radio(
        "Correction saisonnière",
        options=list(SEASONAL_LABELS.keys()),
        format_func=lambda k: SEASONAL_LABELS[k],
        index=0,
        help=(
            "CVS-CJO : recommandé pour analyser la tendance de fond — corrige les effets saisonniers "
            "(ex. : Noël, vacances) et le nombre de jours ouvrables. "
            "Brut : données non corrigées, utiles pour observer les cycles saisonniers eux-mêmes."
        ),
    )
    with st.spinner("Chargement des activités..."):
        acts_df = get_available_activities(idx_type)

    act_options = [str(a) for a in acts_df["ACTIVITY"]]
    act_labels = {a: f"{a} — {activity_labels.get(a, a)}" for a in act_options}

    default_idx = 0
    for i, a in enumerate(act_options):
        if "." not in a:
            default_idx = i
            break

    activity = st.selectbox(
        "Activité",
        options=act_options,
        index=default_idx,
        format_func=lambda k: act_labels[k],
        help=(
            "Code NAF (Nomenclature d'Activités Française). "
            "Les codes courts sans point (ex. C, G) désignent de grands ensembles sectoriels. "
            "Les codes avec point (ex. 10.1) correspondent à des sous-activités plus précises."
        ),
    )

    # Only meaningful when the main series is not already raw
    show_both = st.checkbox(
        "Superposer brut et CVS-CJO",
        value=False,
        disabled=seasonal == "N",
        help="Non disponible quand la série sélectionnée est déjà brute.",
    )

with st.spinner("Chargement de la série..."):
    df = get_time_series(activity, idx_type, seasonal)
    df_raw = get_time_series(activity, idx_type, "N") if (show_both and seasonal != "N") else None

if df.empty:
    st.warning("Aucune donnée disponible pour cette sélection.")
    st.stop()

label = activity_labels.get(activity, activity)
st.subheader(f"{label} ({activity})")
st.caption(f"Indice : {IDX_TYPE_LABELS[idx_type]} · {SEASONAL_LABELS[seasonal]} · Base 2021 = 100")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df["TIME_PERIOD"],
    y=df["OBS_VALUE"],
    name=SEASONAL_LABELS[seasonal],
    mode="lines",
    line=dict(width=2),
    hovertemplate="%{x|%b %Y}: <b>%{y:.2f} pts</b><extra></extra>",
))

if df_raw is not None and not df_raw.empty:
    fig.add_trace(go.Scatter(
        x=df_raw["TIME_PERIOD"],
        y=df_raw["OBS_VALUE"],
        name="Brut",
        mode="lines",
        line=dict(width=1, dash="dot", color="lightgrey"),
        hovertemplate="%{x|%b %Y}: %{y:.2f} pts<extra>Brut</extra>",
    ))

fig.add_hline(y=100, line_dash="dot", line_color="grey", annotation_text="Base 2021 = 100")
fig.update_layout(
    xaxis_title=None,
    yaxis_title="Indice (base 2021 = 100)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    hovermode="x unified",
    height=450,
    margin=dict(t=40, b=0),
)
st.plotly_chart(fig, width="stretch")
st.caption(
    "Chaque point représente la valeur de l'indice pour un mois donné. "
    "La ligne pointillée à 100 est le niveau de référence (moyenne 2021). "
    "Survolez le graphique pour lire la valeur exacte de chaque mois."
)

# Stats summary
latest = df.iloc[-1]
oldest = df.iloc[0]
peak = df.loc[df["OBS_VALUE"].idxmax()]
trough = df.loc[df["OBS_VALUE"].idxmin()]

c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Dernière valeur",
    f"{latest['OBS_VALUE']:.2f} pts",
    f"{latest['TIME_PERIOD'].strftime('%b %Y')}",
    help=(
        "Dernier point publié par l'INSEE pour cette activité. "
        "Les données les plus récentes sont souvent provisoires et peuvent être légèrement révisées "
        "lors des publications suivantes."
    ),
)
c2.metric(
    "Variation depuis début de série",
    f"{((latest['OBS_VALUE'] / oldest['OBS_VALUE']) - 1) * 100:+.1f}%",
    f"depuis {oldest['TIME_PERIOD'].strftime('%b %Y')}",
    help=(
        f"Croissance totale entre la première valeur disponible ({oldest['TIME_PERIOD'].strftime('%b %Y')}) "
        "et le dernier point publié. Indique si le secteur a globalement progressé ou reculé "
        "sur l'ensemble de la période couverte."
    ),
)
c3.metric(
    "Maximum historique",
    f"{peak['OBS_VALUE']:.2f} pts",
    peak["TIME_PERIOD"].strftime("%b %Y"),
    help=(
        "Valeur la plus haute atteinte par cet indice depuis le début de la série. "
        "Un indice récent proche de ce maximum signale une activité particulièrement dynamique."
    ),
)
c4.metric(
    "Minimum historique",
    f"{trough['OBS_VALUE']:.2f} pts",
    trough["TIME_PERIOD"].strftime("%b %Y"),
    help=(
        "Valeur la plus basse enregistrée. "
        "Correspond souvent à un choc économique ponctuel (crise financière, pandémie, etc.)."
    ),
)

st.divider()
st.subheader("Données brutes")
st.caption(
    "Valeurs mensuelles telles que publiées par l'INSEE. "
    "La colonne Statut indique si la donnée est définitive, provisoire ou estimée. "
    "Les données provisoires peuvent être révisées lors de la publication suivante."
)
st.dataframe(
    df.rename(columns={"TIME_PERIOD": "Période", "OBS_VALUE": "Indice", "OBS_STATUS_FR": "Statut"})
    .sort_values("Période", ascending=False)
    .assign(Période=lambda d: d["Période"].dt.strftime("%Y-%m"))
    .reset_index(drop=True),
    width="stretch",
    height=300,
)
