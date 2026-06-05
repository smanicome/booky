# Booky

A Streamlit dashboard visualising French monthly turnover indices (Indices de Chiffres d'Affaires, ICA) published by INSEE. Data covers industry, construction, commerce, and services (base 2021 = 100).

## Pages

- **Accueil** — sector KPI cards and multi-sector trend overview
- **Tendances** — interactive time-series explorer by activity, index type, and seasonal adjustment
- **Marches** — domestic vs. export market split for manufacturing
- **Commerce** — turnover value (ICA_COMM) vs. sales volume (IVVC) with price-effect gap
- **Classement** — growth ranking across all activities for a chosen period

## Requirements

- Python 3.12+
- Dependencies listed in `requirements.txt`

## Local setup

```bash
# Install dependencies
pip install -r requirements.txt

# Preprocess raw CSVs into Parquet (required before first run)
python preprocess.py

# Run the app
streamlit run app/Accueil.py
```

The app detects the absence of `S3_BUCKET` and reads data from `out/` automatically.

## Data flow

```
datasets/DS_ICA_CSV_FR/*.csv
        |
        v  preprocess.py
out/data.parquet + out/metadata.json
        |                   |
        v  local mode        v  S3 mode (S3_BUCKET set)
DuckDB reads file://...  DuckDB reads s3://... via httpfs
```

## Environment variables

Copy `.env.example` to `.env` and fill in the values. Only required for S3 mode (production).

| Variable | Description |
|---|---|
| `S3_BUCKET` | S3 bucket name where the preprocessed files are stored |
| `S3_PREFIX` | Key prefix inside the bucket (default: `ica`) |
| `AWS_DEFAULT_REGION` | AWS region (default: `eu-west-3`) |
| `AWS_ACCESS_KEY_ID` | AWS credentials — not needed when using an IAM task role |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials — not needed when using an IAM task role |

## Deployment

### Preprocess and upload to S3

```bash
python preprocess.py --upload
```

### Build and push to ECR

```bash
docker buildx build --platform linux/amd64 -t booky .
docker tag booky:latest <account-id>.dkr.ecr.eu-west-3.amazonaws.com/booky:latest
docker push <account-id>.dkr.ecr.eu-west-3.amazonaws.com/booky:latest
```

### Run locally with Docker

```bash
docker build -t booky .
docker run -p 8501:8501 --env-file .env booky
```

The production setup runs on AWS ECS Fargate behind an Application Load Balancer. The container reads data from S3 via DuckDB's httpfs extension, authenticated through an IAM task role — no static credentials are needed in the environment.
