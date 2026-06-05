# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A Streamlit dashboard visualising French monthly turnover indices (Indices de Chiffres d'Affaires, ICA) published by INSEE. Data covers industry, construction, commerce, and services (base 2021 = 100).

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Preprocess raw CSVs into Parquet (required before first run)
python preprocess.py

# Preprocess and upload artifacts to S3 (for deployment)
python preprocess.py --upload

# Run the app locally
streamlit run app/Accueil.py

# Build and run with Docker (production mode, reads from S3)
docker build -t booky .
docker run -p 8501:8501 --env-file .env booky
```

## Architecture

### Data flow

```
datasets/DS_ICA_CSV_FR/*.csv
        │
        ▼  preprocess.py (one-time)
out/data.parquet + out/metadata.json
        │                   │
        ▼  local mode        ▼  S3 mode (S3_BUCKET set)
DuckDB reads file://...  DuckDB reads s3://... via httpfs
```

`connection.py` decides local vs. S3 by checking whether `S3_BUCKET` is set in the environment. In S3 mode the DuckDB connection installs and loads the `httpfs` extension and authenticates via credential chain.

### Module layout

- `preprocess.py` — standalone ETL; strips useless columns, casts categories, sorts, outputs Parquet + JSON metadata lookup
- `app/Home.py` — Streamlit entry point; sector KPI cards + multi-sector trend chart
- `app/data/connection.py` — `get_connection()` (DuckDB, `@st.cache_resource`) and `get_metadata()` / `get_data_url()` (local/S3 dispatch)
- `app/data/queries.py` — all DuckDB queries, each wrapped in `@st.cache_data(ttl=None)` (data is static so cache never expires)
- `app/data/constants.py` — `SECTOR_AGGREGATES` mapping (sector label → `(ACTIVITY, IDX_TYPE)` tuple), plus label dicts for index types, seasonal adjustment codes, and market codes
- `app/pages/` — four Streamlit pages, numbered for sidebar order:
  - `1_Tendances.py` — interactive time-series explorer (any activity × index type × seasonal adjustment)
  - `2_Marches.py` — domestic vs. export market split for manufacturing (ICA_INDCONS only)
  - `3_Commerce.py` — turnover value (ICA_COMM) vs. sales volume (IVVC) with price-effect gap
  - `4_Classement.py` — growth ranking across all activities for a chosen period

### Import pattern

Each page does `sys.path.insert(0, str(Path(__file__).parent.parent))` to make `data/` importable as a package, because Streamlit runs pages as top-level scripts.

### Key data columns

`ACTIVITY` (NAF code), `IDX_TYPE` (`ICA_INDCONS` / `ICA_COMM` / `ICA_SERV` / `IPS` / `IVVC`), `SEASONAL_ADJUST` (`Y`=CVS-CJO, `N`=raw, `W`=CJO only), `MARCHE` (`_T`=total, `F`=domestic, `W`=export), `TIME_PERIOD` (YYYY-MM string in Parquet, converted to datetime in queries), `OBS_VALUE` (float).

## Environment

Copy `.env.example` to `.env` and fill in AWS credentials only when deploying to S3. For local development no `.env` is needed — the app detects the absence of `S3_BUCKET` and reads from `out/`.
