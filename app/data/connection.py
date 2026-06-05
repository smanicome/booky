import os
import json
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

REGION = os.environ.get("AWS_DEFAULT_REGION", "eu-west-3")
_OUT_DIR = Path(__file__).parent.parent.parent / "out"


def _is_local() -> bool:
    return not os.environ.get("S3_BUCKET")


@st.cache_resource
def get_connection():
    import duckdb
    con = duckdb.connect()
    if not _is_local():
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute(f"SET s3_region='{REGION}';")
        con.execute("CREATE OR REPLACE SECRET aws_creds (TYPE S3, PROVIDER CREDENTIAL_CHAIN);")
    return con


@st.cache_data(ttl=None)
def get_metadata() -> dict[str, dict[str, str]]:
    if _is_local():
        with open(_OUT_DIR / "metadata.json", encoding="utf-8") as f:
            return json.load(f)
    import boto3
    bucket = os.environ["S3_BUCKET"]
    prefix = os.environ.get("S3_PREFIX", "ica")
    s3 = boto3.client("s3", region_name=REGION)
    obj = s3.get_object(Bucket=bucket, Key=f"{prefix}/metadata.json")
    return json.loads(obj["Body"].read())


def get_data_url() -> str:
    if _is_local():
        return str(_OUT_DIR / "data.parquet")
    bucket = os.environ["S3_BUCKET"]
    prefix = os.environ.get("S3_PREFIX", "ica")
    return f"s3://{bucket}/{prefix}/data.parquet"
