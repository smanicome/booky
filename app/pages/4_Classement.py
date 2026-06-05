import sys
from pathlib import Path
import streamlit as st
import plotly.express as px

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.queries import get_rankings
from data.connection import get_metadata
from data.constants import IDX_TYPE_LABELS
from data.styles import inject_css, render_header, get_page_icon

st.set_page_config(page_title="Booky", layout="wide", page_icon=get_page_icon())
inject_css()
render_header()
st.title("Classement des activités par croissance")
st.caption("Classement des activités économiques selon leur variation d'indice sur une période choisie.")

with st.expander("Comprendre cette page"):
    st.markdown("""
**Comment est calculé le classement ?**

Pour chaque activité économique, on compare l'indice à la date de début et l'indice à la date de fin choisies. La variation est calculée ainsi :

> *Variation (%) = (indice final ÷ indice initial − 1) × 100*

Par exemple, si l'indice d'une activité passe de 95 à 114 entre deux dates, sa variation est de +20 %.

**Comment choisir la période ?**

- Une **période courte** (ex. 3 à 6 mois) mesure une dynamique récente, mais est sensible aux chocs ponctuels.
- Une **période longue** (ex. plusieurs années) donne une vision structurelle de la croissance d'un secteur.
- Comparer **le même mois sur deux années différentes** élimine les effets saisonniers.

**CVS-CJO vs brut**

Utiliser des données **CVS-CJO** est recommandé : en données brutes, une activité dont le mois de début tombe en plein pic saisonnier peut paraître en déclin alors qu'elle se porte bien.

**Lire les deux graphiques**

- **Top** (à gauche) : les activités dont l'indice a le plus progressé sur la période — secteurs en expansion.
- **Flop** (à droite) : les activités dont l'indice a le plus reculé — secteurs en contraction ou en restructuration.

Un secteur absent des deux graphiques a une croissance proche de zéro sur la période.
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
            "Choisissez le type d'indice à classer. Comparer des types différents n'a pas de sens : "
            "chaque type mesure une réalité économique distincte (valeur, volume, production)."
        ),
    )
    seasonal = st.radio(
        "Correction saisonnière",
        ["Y", "N"],
        format_func=lambda k: "CVS-CJO" if k == "Y" else "Brut",
        help=(
            "CVS-CJO recommandé : évite qu'un mois de référence tombant en période haute ou basse "
            "saisonnière fausse le classement. En données brutes, une activité saisonnière peut "
            "sembler en déclin simplement parce que la date de début était un pic."
        ),
    )
    st.divider()
    st.header("Période de comparaison")

    MONTHS = {
        "Janvier": "01", "Février": "02", "Mars": "03", "Avril": "04",
        "Mai": "05", "Juin": "06", "Juillet": "07", "Août": "08",
        "Septembre": "09", "Octobre": "10", "Novembre": "11", "Décembre": "12",
    }
    YEARS = [str(y) for y in range(2000, 2027)]

    st.caption("Début")
    sc1, sc2 = st.columns(2)
    start_month = sc1.selectbox("Mois##start", list(MONTHS.keys()), index=0, label_visibility="collapsed")
    start_year  = sc2.selectbox("Année##start", YEARS, index=YEARS.index("2021"), label_visibility="collapsed")

    st.caption("Fin")
    ec1, ec2 = st.columns(2)
    end_month = ec1.selectbox("Mois##end", list(MONTHS.keys()), index=0, label_visibility="collapsed")
    end_year  = ec2.selectbox("Année##end", YEARS, index=YEARS.index("2026"), label_visibility="collapsed")

    start = f"{start_year}-{MONTHS[start_month]}"
    end   = f"{end_year}-{MONTHS[end_month]}"
    top_n = st.slider(
        "Nombre d'activités affichées (haut / bas)",
        min_value=5,
        max_value=30,
        value=15,
        help="Nombre de secteurs à afficher dans chaque graphique (les N plus fortes hausses à gauche, les N plus fortes baisses à droite).",
    )

with st.spinner("Calcul des croissances..."):
    df = get_rankings(idx_type, seasonal, start, end)

if df.empty:
    st.warning("Aucune donnée pour cette combinaison. Vérifiez les périodes saisies.")
    st.stop()

df["label"] = df["ACTIVITY"].map(lambda a: f"{a} — {activity_labels.get(a, a)}")

st.subheader(f"Top {top_n} — Plus forte croissance")
top = df.head(top_n).copy()
fig_top = px.bar(
    top[::-1],
    x="growth_pct",
    y="label",
    orientation="h",
    color="growth_pct",
    color_continuous_scale=["#aec7e8", "#1f77b4"],
    text="growth_pct",
    labels={"growth_pct": "Variation (%)", "label": ""},
)
fig_top.update_traces(texttemplate="%{text:+.1f}%", textposition="outside")
fig_top.update_layout(coloraxis_showscale=False, margin=dict(t=10, b=0), height=50 + top_n * 28)
st.plotly_chart(fig_top, width="stretch")
st.caption(
    "Activités dont le chiffre d'affaires a le plus progressé entre les deux dates. "
    "Une forte croissance peut refléter un rebond après une crise, une expansion structurelle "
    "ou un effet de rattrapage — comparez avec la période pour l'interpréter correctement."
)

st.subheader(f"Flop {top_n} — Plus forte baisse")
bottom = df.tail(top_n).copy()
fig_bot = px.bar(
    bottom,
    x="growth_pct",
    y="label",
    orientation="h",
    color="growth_pct",
    color_continuous_scale=["#d62728", "#f7b6b6"],
    text="growth_pct",
    labels={"growth_pct": "Variation (%)", "label": ""},
)
fig_bot.update_traces(texttemplate="%{text:+.1f}%", textposition="outside")
fig_bot.update_layout(coloraxis_showscale=False, margin=dict(t=10, b=0), height=50 + top_n * 28)
st.plotly_chart(fig_bot, width="stretch")
st.caption(
    "Activités dont le chiffre d'affaires a le plus reculé entre les deux dates. "
    "Cela peut indiquer une contraction de la demande, une restructuration sectorielle, "
    "ou un effet de base défavorable si la date de début était un pic d'activité."
)

st.divider()
with st.expander(f"Toutes les activités ({len(df)})"):
    st.caption(
        f"Variation calculée comme (indice {end} ÷ indice {start} − 1) × 100. "
        "Seules les activités disposant de données aux deux dates sont incluses. "
        "Vert = croissance, rouge = recul."
    )
    display = df[["label", "val_start", "val_end", "growth_pct"]].copy()
    display.columns = ["Activité", f"Indice {start} (pts)", f"Indice {end} (pts)", "Variation (%)"]
    st.dataframe(
        display.style.format({
            f"Indice {start} (pts)": "{:.2f}",
            f"Indice {end} (pts)": "{:.2f}",
            "Variation (%)": "{:+.2f}%",
        }).map(
            lambda v: "color: #d62728" if isinstance(v, float) and v < 0 else ("color: #2ca02c" if isinstance(v, float) and v > 0 else ""),
            subset=["Variation (%)"],
        ),
        width="stretch",
        height=400,
    )
