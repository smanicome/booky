import os
import json
import duckdb
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

REGION = os.environ.get("AWS_DEFAULT_REGION", "eu-west-3")
_OUT_DIR = Path(__file__).parent.parent.parent / "out"
# Recreate the connection (and its S3 secret) well before typical STS/role
# token lifetimes (commonly 1h) so CREDENTIAL_CHAIN re-resolves fresh creds.
_CONNECTION_TTL = 1800


def _is_local() -> bool:
    return not os.environ.get("S3_BUCKET")


@st.cache_resource(ttl=_CONNECTION_TTL)
def get_connection():
    con = duckdb.connect()
    if not _is_local():
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute(f"SET s3_region='{REGION}';")
        con.execute("CREATE OR REPLACE SECRET aws_creds (TYPE S3, PROVIDER CREDENTIAL_CHAIN);")
    return con


def execute_df(query: str, params: list | None = None):
    """Run a query against the cached connection, returning a DataFrame.

    DuckDB's CREDENTIAL_CHAIN secret never auto-refreshes, so if the AWS
    token expired mid-TTL the S3 read fails with an IOException; in that
    case drop the cached connection and retry once with fresh credentials.
    """
    try:
        return get_connection().execute(query, params or []).df()
    except duckdb.IOException:
        if _is_local():
            raise
        get_connection.clear()
        return get_connection().execute(query, params or []).df()


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
