"""Daily mortgage ELT: land servicing files -> dbt build (models + tests) -> freshness/docs.

dbt runs as one Airflow task per layer so a failing staging test stops the marts
from being rebuilt on bad data, and retries are scoped to the layer that failed.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT = "/opt/airflow/project"
DBT = f"cd {PROJECT}/dbt && dbt --no-use-colors"
DBT_ENV = {"DUCKDB_PATH": f"{PROJECT}/warehouse.duckdb", "DBT_PROFILES_DIR": f"{PROJECT}/dbt"}

default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "execution_timeout": timedelta(minutes=45),
}

with DAG(
    dag_id="mortgage_portfolio_elt",
    description="Mortgage origination + servicing ELT into portfolio marts",
    start_date=datetime(2026, 1, 1),
    schedule="0 6 * * *",
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["mortgage", "dbt", "elt"],
) as dag:
    extract_load = BashOperator(
        task_id="extract_load_raw",
        bash_command=f"python {PROJECT}/ingestion/generate_and_load.py --db {PROJECT}/warehouse.duckdb --landing {PROJECT}/data/landing",
    )

    source_freshness = BashOperator(
        task_id="dbt_source_freshness",
        bash_command=f"{DBT} source freshness",
        env=DBT_ENV,
        append_env=True,
    )

    layers = {}
    for layer in ["staging", "intermediate", "marts"]:
        layers[layer] = BashOperator(
            task_id=f"dbt_build_{layer}",
            bash_command=f"{DBT} build --select path:models/{layer} --fail-fast",
            env=DBT_ENV,
            append_env=True,
        )

    singular_tests = BashOperator(
        task_id="dbt_singular_tests",
        bash_command=f"{DBT} test --select test_type:singular",
        env=DBT_ENV,
        append_env=True,
    )

    docs = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=f"{DBT} docs generate",
        env=DBT_ENV,
        append_env=True,
        trigger_rule="all_success",
    )

    extract_load >> source_freshness >> layers["staging"] >> layers["intermediate"] >> layers["marts"] >> singular_tests >> docs
