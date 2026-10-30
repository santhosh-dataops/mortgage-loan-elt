# Mortgage Portfolio ELT — Airflow + dbt

Batch ELT pipeline that lands mortgage **origination** and monthly **servicing** data, then uses dbt to build tested, analytics-ready marts for portfolio risk reporting: delinquency rates, roll rates and current loan status.

![CI](https://github.com/santhosh-dataops/mortgage-loan-elt/actions/workflows/ci.yml/badge.svg)

## Architecture

```
 Origination + servicing files
            │  ingestion/generate_and_load.py  (validate → atomic swap)
            ▼
  raw.loan_origination / raw.loan_servicing        (DuckDB locally, Snowflake in prod)
            │  dbt
            ▼
  staging      stg_loans, stg_servicing            typing, credit tiers
  intermediate int_loan_month_status               delinquency buckets, prior-month state (LAG)
  marts        dim_loan, fct_portfolio_monthly     KPIs: DQ rate by count & UPB, roll rates
            ▲
  Airflow DAG: extract_load → source freshness → build staging → intermediate → marts → singular tests → docs
```

## Highlights

- **Layered dbt project** with staging / intermediate / marts schemas and a custom `generate_schema_name` macro.
- **Data quality gates**: uniqueness, not-null, accepted values, referential integrity, a composite-key generic test written without packages, and singular business-rule tests (UPB sanity, rates bounded 0–1).
- **Source freshness** checks before any model is rebuilt.
- **Layer-by-layer Airflow tasks** with `--fail-fast`, so a failing staging test stops marts from being rebuilt on bad data, and retries are scoped to the layer that failed.
- **Idempotent, validated loads**: duplicate keys and nulls are rejected before data reaches `raw`, and tables are swapped in a single transaction.
- **Warehouse-portable**: the same models run on DuckDB (dev/CI) or Snowflake (`--target prod`).

## Quick start

```bash
pip install -r requirements.txt
python ingestion/generate_and_load.py --db warehouse.duckdb --loans 3000 --months 18
cd dbt && DBT_PROFILES_DIR=. DUCKDB_PATH=../warehouse.duckdb dbt build
```

Sample output (`marts.fct_portfolio_monthly`, 30Y fixed, one month):

| credit_tier | active_loans | dq_rate_upb | roll_rate_current_to_30 |
|---|---|---|---|
| SUPER_PRIME | 289 | 0.0388 | 0.0144 |
| PRIME | 451 | 0.0697 | 0.0216 |
| NEAR_PRIME | 188 | 0.0945 | 0.0452 |

Run the orchestrated version:

```bash
cd airflow && docker compose up     # UI at http://localhost:8080, DAG: mortgage_portfolio_elt
```

## Tests

```bash
pytest -q            # ingestion unit tests
cd dbt && dbt test   # 20 data tests
```

## Tech
Python · dbt · DuckDB · Snowflake · Apache Airflow · SQL · Docker · PyTest · GitHub Actions
