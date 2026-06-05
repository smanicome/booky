import pandas as pd
import streamlit as st
from .connection import get_connection, get_data_url
from .constants import SECTOR_AGGREGATES


@st.cache_data(ttl=None)
def get_sector_dashboard() -> pd.DataFrame:
    """Latest index value + MoM and YoY changes for each top-level sector."""
    con = get_connection()
    url = get_data_url()

    rows = []
    for sector, (activity, idx_type) in SECTOR_AGGREGATES.items():
        df = con.execute(
            f"""
            SELECT TIME_PERIOD, OBS_VALUE
            FROM read_parquet('{url}')
            WHERE ACTIVITY = ?
              AND IDX_TYPE = ?
              AND SEASONAL_ADJUST = 'Y'
              AND MARCHE = '_T'
            ORDER BY TIME_PERIOD DESC
            LIMIT 14
            """,
            [activity, idx_type],
        ).df()

        if df.empty:
            continue

        df = df.sort_values("TIME_PERIOD", ascending=False).reset_index(drop=True)
        latest_period = df.loc[0, "TIME_PERIOD"]
        latest_val = df.loc[0, "OBS_VALUE"]

        # Use actual date arithmetic instead of positional indexing to handle gaps
        mom_row = df[df["TIME_PERIOD"] == _shift_month(latest_period, -1)]
        yoy_row = df[df["TIME_PERIOD"] == _shift_month(latest_period, -12)]

        mom = ((latest_val / mom_row.iloc[0]["OBS_VALUE"]) - 1) * 100 if not mom_row.empty else None
        yoy = ((latest_val / yoy_row.iloc[0]["OBS_VALUE"]) - 1) * 100 if not yoy_row.empty else None

        rows.append({
            "Secteur": sector,
            "Période": latest_period,
            "Indice (base 2021)": round(latest_val, 2),
            "Variation mensuelle (%)": round(mom, 2) if mom is not None else None,
            "Variation annuelle (%)": round(yoy, 2) if yoy is not None else None,
        })

    return pd.DataFrame(rows)


def _shift_month(period: str, delta: int) -> str:
    """Return a YYYY-MM string shifted by `delta` months."""
    import datetime
    year, month = int(period[:4]), int(period[5:7])
    month += delta
    year += (month - 1) // 12
    month = (month - 1) % 12 + 1
    return f"{year}-{month:02d}"


@st.cache_data(ttl=None)
def get_time_series(
    activity: str,
    idx_type: str,
    seasonal_adjust: str,
    marche: str = "_T",
) -> pd.DataFrame:
    con = get_connection()
    url = get_data_url()
    df = con.execute(
        f"""
        SELECT TIME_PERIOD, OBS_VALUE, OBS_STATUS_FR
        FROM read_parquet('{url}')
        WHERE ACTIVITY = ?
          AND IDX_TYPE = ?
          AND SEASONAL_ADJUST = ?
          AND MARCHE = ?
        ORDER BY TIME_PERIOD
        """,
        [activity, idx_type, seasonal_adjust, marche],
    ).df()
    df["TIME_PERIOD"] = pd.to_datetime(df["TIME_PERIOD"], format="%Y-%m")
    return df


@st.cache_data(ttl=None)
def get_available_activities(idx_type: str) -> pd.DataFrame:
    con = get_connection()
    url = get_data_url()
    return con.execute(
        f"""
        SELECT ACTIVITY, COUNT(*) as n
        FROM read_parquet('{url}')
        WHERE IDX_TYPE = ?
          AND SEASONAL_ADJUST = 'Y'
          AND MARCHE = '_T'
        GROUP BY ACTIVITY
        ORDER BY ACTIVITY
        """,
        [idx_type],
    ).df()


@st.cache_data(ttl=None)
def get_activities_with_market_split() -> pd.DataFrame:
    """Activities that have both domestic (F) and export (W) breakdown in ICA_INDCONS CVS-CJO."""
    con = get_connection()
    url = get_data_url()
    return con.execute(
        f"""
        SELECT ACTIVITY, COUNT(*) as n
        FROM read_parquet('{url}')
        WHERE IDX_TYPE = 'ICA_INDCONS'
          AND SEASONAL_ADJUST = 'Y'
          AND MARCHE IN ('F', 'W')
        GROUP BY ACTIVITY
        HAVING COUNT(DISTINCT MARCHE) = 2
        ORDER BY ACTIVITY
        """,
    ).df()


@st.cache_data(ttl=None)
def get_market_split(activity: str) -> pd.DataFrame:
    """Domestic vs export time series for a manufacturing activity."""
    con = get_connection()
    url = get_data_url()
    df = con.execute(
        f"""
        SELECT TIME_PERIOD, MARCHE, OBS_VALUE
        FROM read_parquet('{url}')
        WHERE ACTIVITY = ?
          AND IDX_TYPE = 'ICA_INDCONS'
          AND SEASONAL_ADJUST = 'Y'
          AND MARCHE IN ('_T', 'F', 'W')
        ORDER BY TIME_PERIOD, MARCHE
        """,
        [activity],
    ).df()
    df["TIME_PERIOD"] = pd.to_datetime(df["TIME_PERIOD"], format="%Y-%m")
    df["MARCHE"] = df["MARCHE"].map({"_T": "Total", "F": "Marché intérieur", "W": "Marché extérieur"})
    return df


@st.cache_data(ttl=None)
def get_commerce_value_vs_volume(activity: str) -> pd.DataFrame:
    """Turnover value (ICA_COMM) vs sales volume (IVVC) for a commerce activity."""
    con = get_connection()
    url = get_data_url()
    df = con.execute(
        f"""
        SELECT TIME_PERIOD, IDX_TYPE, OBS_VALUE
        FROM read_parquet('{url}')
        WHERE ACTIVITY = ?
          AND IDX_TYPE IN ('ICA_COMM', 'IVVC')
          AND SEASONAL_ADJUST = 'Y'
          AND MARCHE = '_T'
        ORDER BY TIME_PERIOD, IDX_TYPE
        """,
        [activity],
    ).df()
    df["TIME_PERIOD"] = pd.to_datetime(df["TIME_PERIOD"], format="%Y-%m")
    df["IDX_TYPE"] = df["IDX_TYPE"].map({"ICA_COMM": "Valeur (CA)", "IVVC": "Volume des ventes"})
    return df


@st.cache_data(ttl=None)
def get_rankings(idx_type: str, seasonal_adjust: str, start: str, end: str) -> pd.DataFrame:
    """Growth ranking for all activities of a given index type between two periods."""
    con = get_connection()
    url = get_data_url()
    df = con.execute(
        f"""
        WITH bounds AS (
            SELECT ACTIVITY,
                   MAX(CASE WHEN TIME_PERIOD = ? THEN OBS_VALUE END) AS val_start,
                   MAX(CASE WHEN TIME_PERIOD = ? THEN OBS_VALUE END) AS val_end
            FROM read_parquet('{url}')
            WHERE IDX_TYPE = ?
              AND SEASONAL_ADJUST = ?
              AND MARCHE = '_T'
              AND TIME_PERIOD IN (?, ?)
            GROUP BY ACTIVITY
        )
        SELECT ACTIVITY,
               val_start,
               val_end,
               ROUND((val_end / val_start - 1) * 100, 2) AS growth_pct
        FROM bounds
        WHERE val_start IS NOT NULL AND val_end IS NOT NULL AND val_start > 0
        ORDER BY growth_pct DESC
        """,
        [start, end, idx_type, seasonal_adjust, start, end],
    ).df()
    return df
