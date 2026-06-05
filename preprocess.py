"""
One-time preprocessing script: converts raw CSVs to Parquet, optionally uploads to S3.

Local only (no AWS needed):
    python preprocess.py

Upload to S3 (for deployment):
    python preprocess.py --upload
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent / "datasets" / "DS_ICA_CSV_FR"
OUT_DIR = Path(__file__).parent / "out"
OUT_DIR.mkdir(exist_ok=True)

USELESS_COLS = {"FREQ", "BASE_PER", "UNIT_MEASURE", "DECIMALS", "EMBARGO_DATE"}


def build_data_parquet() -> Path:
    print("Reading data CSV...")
    df = pd.read_csv(
        DATA_DIR / "DS_ICA_data.csv",
        sep=";",
        quotechar='"',
        dtype=str,
    )

    df.drop(columns=[c for c in USELESS_COLS if c in df.columns], inplace=True)
    df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")

    df = df[df["CONF_STATUS"] != "C"].dropna(subset=["OBS_VALUE"])

    for col in ("ACTIVITY", "SEASONAL_ADJUST", "IDX_TYPE", "MARCHE", "OBS_STATUS", "OBS_STATUS_FR", "INDICATOR", "CONF_STATUS"):
        if col in df.columns:
            df[col] = df[col].astype("category")

    df.sort_values(["IDX_TYPE", "ACTIVITY", "SEASONAL_ADJUST", "MARCHE", "TIME_PERIOD"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    out = OUT_DIR / "data.parquet"
    df.to_parquet(out, index=False, engine="pyarrow", compression="snappy")
    print(f"  → {out} ({out.stat().st_size / 1_048_576:.1f} MB)")
    return out


def build_metadata_json() -> Path:
    print("Reading metadata CSV...")
    meta = pd.read_csv(DATA_DIR / "DS_ICA_metadata.csv", sep=";", quotechar='"', dtype=str)

    lookup: dict[str, dict[str, str]] = {}
    for _, row in meta.iterrows():
        var = row["COD_VAR"]
        lookup.setdefault(var, {})[row["COD_MOD"]] = row["LIB_MOD"]

    out = OUT_DIR / "metadata.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(lookup, f, ensure_ascii=False, indent=2)
    print(f"  → {out} ({out.stat().st_size / 1024:.1f} KB)")
    return out


def upload_to_s3(path: Path) -> None:
    import boto3
    bucket = os.environ.get("S3_BUCKET")
    if not bucket:
        raise EnvironmentError("S3_BUCKET is not set in your .env file.")
    prefix = os.environ.get("S3_PREFIX", "ica")
    s3 = boto3.client("s3")
    key = f"{prefix}/{path.name}"
    print(f"Uploading s3://{bucket}/{key} ...")
    s3.upload_file(str(path), bucket, key)
    print("  done.")


if __name__ == "__main__":
    upload = "--upload" in sys.argv

    data_path = build_data_parquet()
    meta_path = build_metadata_json()

    if upload:
        upload_to_s3(data_path)
        upload_to_s3(meta_path)
        print("Preprocessing and upload complete.")
    else:
        print("Preprocessing complete. Run with --upload to push to S3.")
